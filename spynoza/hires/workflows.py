import nipype.pipeline.engine as pe
import nipype.interfaces.utility as niu
from nipype.interfaces import fsl, ants, afni
from nipype.interfaces.base import isdefined
import pkg_resources

from ..utils import average_over_runs, get_scaninfo, init_temporally_crop_run_wf, pickfirst

from ..motion_correction.workflows import create_motion_correction_workflow
from ..unwarping.topup.workflows import create_bids_topup_workflow
from ..unwarping.t1w_epi.workflows import create_t1w_epi_registration_workflow
from ..registration.sub_workflows import create_epi_to_T1_workflow

from spynoza.io.bids_interfaces import collect_data

from niworkflows.interfaces.utils import CopyXForm

# MONKEY PATCH
# =========================

from nipype.interfaces.ants.base import ANTSCommand, ANTSCommandInputSpec
from nipype.interfaces.base import TraitedSpec, File, traits, InputMultiPath

class ComposeMultiTransformInputSpec(ANTSCommandInputSpec):
    dimension = traits.Enum(3, 2, argstr='%d', usedefault=True, position=0,
                            desc='image dimension (2 or 3)')
    output_transform = File(argstr='%s', position=1, name_source=['transforms'],
                            name_template='%s_composed', keep_ext=True,
                            desc='the name of the resulting transform.')
    reference_image = File(argstr='-R %s', position=2,
                           desc='Reference image (only necessary when output is warpfield)')
    transforms = InputMultiPath(File(exists=True), argstr='%s', mandatory=True,
                                position=3, desc='transforms to average')


class ComposeMultiTransformOutputSpec(TraitedSpec):
    output_transform = File(exists=True, desc='Composed transform file')


class ComposeMultiTransform(ANTSCommand):
    """
    Take a set of transformations and convert them to a single transformation matrix/warpfield.
    Examples
    --------
    >>> from nipype.interfaces.ants import ComposeMultiTransform
    >>> compose_transform = ComposeMultiTransform()
    >>> compose_transform.inputs.dimension = 3
    >>> compose_transform.inputs.transforms = ['struct_to_template.mat', 'func_to_struct.mat']
    >>> compose_transform.cmdline # doctest: +ALLOW_UNICODE
    'ComposeMultiTransform 3 struct_to_template_composed struct_to_template.mat func_to_struct.mat'
    """
    _cmd = 'ComposeMultiTransform'
    input_spec = ComposeMultiTransformInputSpec
    output_spec = ComposeMultiTransformOutputSpec

# ========================
def init_hires_unwarping_wf(name="unwarp_hires",
                            method='topup',
                            bids_layout=None,
                            single_warpfield=False,
                            register_to='last',
                            init_reg_file=None,
                            linear_registration_parameters='linear_hires.json',
                            nonlinear_registration_parameters='nonlinear_precise.json',
                            bold_epi=None,
                            epi_op=None,
                            t1w_epi=None,
                            t1w=None,
                            wm_seg=None,
                            cost_func=None,
                            inv2_epi=None,
                            dof=6,
                            crop_bold_epis=True,
                            topup_package='afni',
                            epi_to_t1_package='ants',
                            within_epi_reg=True,
                            polish=True,
                            num_threads_ants=4):
    
    """ Use an EPI with opposite phase-encoding (EPI_op) or a 
    T1-weighted EPI image to unwarp functional MRI data at 7 Tesla.

    This workflow can use three different methods:
     1) 'topup_separate': Unwarp the bold EPI runs separately, 
     using their "own" EPI with opposite phase-encoding (EPI_op)
     2) topup_combined: make a mean bold EPI and EPI_op and make _one_
     unwarp field applied to all bold EPIs.
     3) Linearly register the EPIs to a T1-weighted image using EPI readout 
     (T1w_epi). Register the T1w_epi non-linearly to the (undistorted) T1w. 
     
    It is important to note that the unwarping of EPIs to the T1
    
    Parameters
    ----------
    name : string
        name of workflow
    method : string
        which method is used to unwarp the bold EPI Possible values are:
         * topup:          Unwarp BOLD EPI runs using EPI_op and TOPUP algorithm.
         * t1w_epi:        Use a T1-weighted image with similar distortions as the 
                           bold EPI.
    single_warpfield : bool
        Whether to make one warpfield for every run separately, or to make only one
        warpfield for *all* runs.
    register_to : string
        Only used when using a single_warpfield. Determines which run is used to register 
        all other bold EPIs to, before making a "combined" warpfield. Should only be set when 
        method == topup_combined.
    linear_registration_parameters : string
        Which parameter to use for linear registration (see file in spynoza/data/ants_json)
    nonlinear_registration_parameters : string
        Which parameter to use for linear registration (see file in spynoza/data/ants_json)        
    within_epi_reg : bool
        Determines whether bold EPIs are linearly registered to the best-fitting bold EPI
        in T1w-space at the end of the pipeline (reccomended).         
    bold_epi : list:
        List of BOLD EPI runs.
    epi_op : list/filename:
        List of EPI runs with opposite-phase encoding. Should be same length as and
        corresponding to bold_epi.
    crop_epi : bool
        Whether or not to crop the BOLD EPIs to the size of their corresponding
        EPI_op.
    t1w : filename
        T1-weighted structural image
    wm_seg : bool
        whether to use wm_seg
    cost_func : 'mutualinfo', 'bbr', or 'corratio'...
        Cost funtion to use for FSL. By default uses BBR, when wm_seg is given,
        otherwise mutualinfo
    t1w_epi : list/filename
        T1-weighted EPI with same distortions as bold_epi.
        
    """


    wf = pe.Workflow(name=name)
    
    fields = ['bold_epi', 'T1w', 'wm_seg']
    
    if method == 'topup':
        fields += ['epi_op',
                   'bold_epi_metadata',
                   'epi_op_metadata']
    elif method == 't1w_epi':
        fields += ['T1w_epi', 'inv2_epi']
    
    inputspec = pe.Node(niu.IdentityInterface(fields=fields),
                        name='inputspec')
    
    if bold_epi:
        inputspec.inputs.bold_epi = bold_epi
        if bids_layout:
            inputspec.inputs.bold_epi_metadata = [bids_layout.get_metadata(epi) for epi in bold_epi]
        
    if epi_op:
        if method == 'topup':
            inputspec.inputs.epi_op = epi_op

            if bids_layout:
                inputspec.inputs.epi_op_metadata = [bids_layout.get_metadata(epi) for epi in epi_op]
        else:
            raise Exception('epi_op can only be set when using TOPUP method')
        
    if t1w_epi:
        if method == 't1w_epi':
            inputspec.inputs.T1w_epi = t1w_epi
        else:
            raise Exception('t1w_epi can only be set when using t1w_epi method')

    if inv2_epi:
        if method == 't1w_epi':
            inputspec.inputs.inv2_epi = inv2_epi
        else:
            raise Exception('inv2_epi can only be set when using t1w_epi method')

    if t1w:
        inputspec.inputs.T1w = t1w

    if wm_seg:
        cost_func = 'bbr'
    else:
        cost_func = 'mutualinfo'
            
    out_fields = ['bold_epi_mc',
                  'bold_epi_mask',
                  'bold_epi_mean',
                  'bold_epi_to_T1w_transforms',
                  'mean_epi_in_T1w_space']
    
    pre_outputnode = pe.Node(niu.IdentityInterface(fields=out_fields),
                             name='pre_outputnode')

    
    #  *** TOPUP ***
    if method == 'topup':
        
        # *** only ONE warpfield ***
        if single_warpfield:

            if within_epi_reg:
                raise Exception('When using a single warpfield for \
                                all BOLD runs, there is little use for within_epi_reging, right?')
            
            mc_wf_bold_epi = create_motion_correction_workflow(name='mc_wf_bold_epi',
                                                               output_mask=True,
                                                               method='FSL',
                                                               lightweight=True)
            
            mc_wf_bold_epi.inputs.inputspec.which_file_is_EPI_space = register_to
            mc_wf_bold_epi.inputs.create_bold_mask.connected=False
            
            
            wf.connect(inputspec, 'bold_epi', mc_wf_bold_epi, 'inputspec.in_files')
                
            
            mc_wf_epi_op = create_motion_correction_workflow(name='mc_wf_epi_op',
                                                             method='FSL',
                                                             output_mask=True,
                                                             lightweight=True)
            
            mc_wf_epi_op.inputs.inputspec.which_file_is_EPI_space = register_to
            mc_wf_epi_op.inputs.create_bold_mask.connected = False

            wf.connect(inputspec, 'epi_op', mc_wf_epi_op, 'inputspec.in_files')
            


            mean_bold_epis1 = pe.MapNode(fsl.MeanImage(dimension='T'), 
                                         iterfield=['in_file'],
                                         name='mean_bold_epis1')
            mean_epis_op1 = pe.MapNode(fsl.MeanImage(dimension='T'), 
                                       iterfield=['in_file'],
                                       name='mean_epis_op1')
            
            
            if crop_bold_epis:
                crop_bold_epi_wf = init_temporally_crop_run_wf()
                wf.connect(mc_wf_bold_epi, 'outputspec.motion_corrected_files', crop_bold_epi_wf, 'inputspec.in_files')
                wf.connect(inputspec, 'epi_op', crop_bold_epi_wf, 'inputspec.templates')
                wf.connect(crop_bold_epi_wf, 'outputspec.out_files', mean_bold_epis1, 'in_file')
            else:
                wf.connect(mc_wf_bold_epi, 'outputspec.motion_corrected_files', mean_bold_epis1, 'in_file')
            
            wf.connect(mc_wf_epi_op, 'outputspec.motion_corrected_files', mean_epis_op1, 'in_file')
            
            mean_bold_epis2 = pe.Node(niu.Function(function=average_over_runs),
                                     name='mean_bold_epis2')
            mean_epi_op2 = pe.Node(niu.Function(function=average_over_runs),
                                     name='mean_epi_op2')
            
            applymask_bold_epi = pe.MapNode(fsl.ApplyMask(),
                                            iterfield=['in_file'],
                                            name="applymask_bold_epi")

            # We mask the bold EPI runs separately, for later use
            wf.connect(mean_bold_epis1, 'out_file', applymask_bold_epi, 'in_file') 
            wf.connect(mc_wf_bold_epi, 'outputspec.EPI_space_mask', applymask_bold_epi, 'mask_file') 

            applymask_epi_op = pe.Node(fsl.ApplyMask(), name="applymask_epi_op")
            wf.connect(mean_epi_op2, 'out', applymask_epi_op, 'in_file') 
            wf.connect(mc_wf_epi_op, 'outputspec.EPI_space_mask', applymask_epi_op, 'mask_file') 

            wf.connect(applymask_bold_epi, 'out_file', mean_bold_epis2, 'in_files')
            wf.connect(mean_epis_op1, 'out_file', mean_epi_op2, 'in_files') 


            topup_wf = create_bids_topup_workflow(package=topup_package)

            wf.connect(mean_bold_epis2, 'out', topup_wf, 'inputspec.bold_epi')
            wf.connect(applymask_epi_op, 'out_file', topup_wf, 'inputspec.epi_op')
            wf.connect(inputspec, ('bold_epi_metadata', pickfirst), topup_wf, 'inputspec.bold_epi_metadata')
            wf.connect(inputspec, ('epi_op_metadata', pickfirst), topup_wf, 'inputspec.epi_op_metadata')

            registration_wf = create_epi_to_T1_workflow(package=epi_to_t1_package,
                                                        num_threads_ants=num_threads_ants,
                                                        dof=dof,
                                                        cost_func=cost_func,
                                                        parameter_file=linear_registration_parameters,
                                                        init_reg_file=init_reg_file)

            wf.connect(inputspec, 'wm_seg', registration_wf, 'inputspec.wm_seg_file')

            wf.connect(topup_wf, 'outputspec.bold_epi_corrected', registration_wf, 'inputspec.EPI_space_file')
            wf.connect(inputspec, 'T1w', registration_wf, 'inputspec.T1_file')
            
            merge_bold_epi_to_T1w = pe.Node(niu.Merge(2), name='merge_bold_epi_to_T1w')
            wf.connect(topup_wf, 'outputspec.bold_epi_unwarp_field', merge_bold_epi_to_T1w, 'in1')
            wf.connect(registration_wf, 'outputspec.EPI_T1_matrix_file', merge_bold_epi_to_T1w, 'in2')

            transform_epi_to_T1w = pe.MapNode(ants.ApplyTransforms(dimension=3,
                                                                float=True,
                                                                num_threads=num_threads_ants,
                                                                interpolation='LanczosWindowedSinc'),
                                              iterfield=['input_image'],
                                              name='transform_epi_to_T1w')

            wf.connect(applymask_bold_epi, 'out_file', transform_epi_to_T1w, 'input_image')
            wf.connect(inputspec, 'T1w', transform_epi_to_T1w, 'reference_image')
            wf.connect(merge_bold_epi_to_T1w, ('out', reverse), transform_epi_to_T1w, 'transforms')

            make_list_of_transforms = pe.Node(niu.Function(function=_make_list_from_element),
                                              name='make_list_of_transforms')

            wf.connect(merge_bold_epi_to_T1w, 'out', make_list_of_transforms, 'element')
            wf.connect(mc_wf_bold_epi, 'outputspec.motion_corrected_files', make_list_of_transforms, 'template_list')

            wf.connect(mc_wf_bold_epi, 'outputspec.motion_corrected_files', pre_outputnode, 'bold_epi_mc')
            wf.connect(mc_wf_bold_epi, 'outputspec.EPI_space_mask', pre_outputnode, 'bold_epi_mask')
            wf.connect(mean_bold_epis1, 'out_file', pre_outputnode, 'bold_epi_mean')
            wf.connect(make_list_of_transforms, 'out', pre_outputnode, 'bold_epi_to_T1w_transforms')
            wf.connect(transform_epi_to_T1w, 'output_image', pre_outputnode, 'mean_epi_in_T1w_space')

        # SEPERATE warpfields for each run
        else:


            if not (isdefined(inputspec.inputs.bold_epi) and isdefined(inputspec.inputs.epi_op)):
                    raise Exception ("When using separate warpfield, bold_epi and epi_op" \
                                    " have to be defined at workflow initialization")
            
            if not (len(inputspec.inputs.bold_epi) == len(inputspec.inputs.epi_op)):
                raise Exception ("Number of bold_epi and epi_op runs should be identical")

            merge_topup_corrections_runs = pe.Node(niu.Merge(len(epi_op)),
                                                   name='merge_topup_corrections_runs')

            merge_epi_to_T1w_transforms_runs = pe.Node(niu.Merge(len(epi_op)),
                                                       name='merge_epi_to_T1w_transforms_runs')

            merge_mean_epis = pe.Node(niu.Merge(len(epi_op)),
                                      name='merge_mean_epis')

            merge_mc_epis = pe.Node(niu.Merge(len(epi_op)),
                                      name='merge_mc_epis')

            merge_epi_masks = pe.Node(niu.Merge(len(epi_op)),
                                      name='merge_epi_masks')

            for ix in range(len(epi_op)):


                run_wf = pe.Workflow(name='run_wf_%d' % ix)

                select_bold_epi = pe.Node(niu.Select(index=ix), 
                                          name='select_bold_epi_%s' % ix)
                select_epi_op = pe.Node(niu.Select(index=ix), 
                                          name='select_epi_op_%s' % ix)

                
                mc_wf_bold_epi = create_motion_correction_workflow(name='mc_wf_bold_epi',
                                                                   output_mask=True,
                                                                   method='FSL',
                                                                   lightweight=True)
                run_wf.connect(select_bold_epi, 'out', mc_wf_bold_epi, 'inputspec.in_files')
                run_wf.connect(select_bold_epi, ('out', pickfirst), mc_wf_bold_epi, 'inputspec.which_file_is_EPI_space')
                wf.connect(inputspec, 'bold_epi', run_wf, 'select_bold_epi_%s.inlist' % ix)
                mc_wf_bold_epi.inputs.create_bold_mask.connected=False

                mc_wf_epi_op = create_motion_correction_workflow(name='mc_wf_epi_ops',
                                                                 method='FSL',
                                                                 output_mask=True,
                                                                 lightweight=True)
                mc_wf_epi_op.inputs.create_bold_mask.connected=False

                run_wf.connect(select_epi_op, 'out', mc_wf_epi_op, 'inputspec.in_files')
                run_wf.connect(select_epi_op, ('out', pickfirst), mc_wf_epi_op, 'inputspec.which_file_is_EPI_space')
                wf.connect(inputspec, 'epi_op', run_wf, 'select_epi_op_%s.inlist' % ix)
            
                mean_bold_epi1 = pe.MapNode(fsl.MeanImage(dimension='T'), 
                                             iterfield=['in_file'],
                                             name='mean_bold_epi1')

                if crop_bold_epis:
                    crop_bold_epi_wf = init_temporally_crop_run_wf(name='crop_run_%s' % ix)
                    run_wf.connect(mc_wf_bold_epi, 'outputspec.motion_corrected_files', crop_bold_epi_wf, 'inputspec.in_files')
                    run_wf.connect(select_epi_op, 'out', crop_bold_epi_wf, 'inputspec.templates')
                    run_wf.connect(crop_bold_epi_wf, 'outputspec.out_files', mean_bold_epi1, 'in_file')
                else:
                    run_wf.connect(mc_wf_bold_epi, 'outputspec.motion_corrected_files', mean_bold_epi1, 'in_file')
            
            
                biasfield_correct_bold_epi = pe.Node(ants.N4BiasFieldCorrection(
                                                dimension=3, copy_header=True),
                                                     name='biasfield_correct_bold_epi')

                correct_header_bold_epi_biasfield = pe.Node(CopyXForm(),
                                                            name='correct_header_bold_epi_biasfield') 


                run_wf.connect(mean_bold_epi1, ('out_file', pickfirst), correct_header_bold_epi_biasfield, 'hdr_file') 
                run_wf.connect(mean_bold_epi1, ('out_file', pickfirst), biasfield_correct_bold_epi, 'input_image') 

                run_wf.connect(biasfield_correct_bold_epi, 'output_image', correct_header_bold_epi_biasfield, 'in_file') 

                applymask_bold_epi = pe.Node(fsl.ApplyMask(),
                                                name="applymask_bold_epi")
                run_wf.connect(correct_header_bold_epi_biasfield, 'out_file', applymask_bold_epi, 'in_file') 
                run_wf.connect(mc_wf_bold_epi, 'outputspec.EPI_space_mask', applymask_bold_epi, 'mask_file') 

                biasfield_correct_epi_op = pe.Node(ants.N4BiasFieldCorrection(
                                              dimension=3, copy_header=True),
                                                     name='biasfield_correct_epi_op')

                correct_header_epi_op_biasfield = pe.Node(CopyXForm(),
                                                            name='correct_header_epi_biasfield') 
                run_wf.connect(mc_wf_epi_op, 'outputspec.EPI_space_file', correct_header_epi_op_biasfield, 'hdr_file') 
                run_wf.connect(biasfield_correct_epi_op, 'output_image', correct_header_epi_op_biasfield, 'in_file') 

                run_wf.connect(mc_wf_epi_op, 'outputspec.EPI_space_file', biasfield_correct_epi_op, 'input_image') 
                applymask_epi_op = pe.Node(fsl.ApplyMask(), name="applymask_epi_op")
                run_wf.connect(correct_header_epi_op_biasfield, 'out_file', applymask_epi_op, 'in_file') 
                run_wf.connect(mc_wf_epi_op, 'outputspec.EPI_space_mask', applymask_epi_op, 'mask_file') 

                topup_wf = create_bids_topup_workflow(package=topup_package)
                topup_wf.get_node('qwarp').inputs.minpatch = 5

                run_wf.connect(applymask_bold_epi, 'out_file', topup_wf, 'inputspec.bold_epi')
                run_wf.connect(applymask_epi_op, 'out_file', topup_wf, 'inputspec.epi_op')

                select_bold_epi_metadata = pe.Node(niu.Select(index=ix), 
                                          name='select_bold_epi_metadata_%s' % ix)
                run_wf.connect(select_bold_epi_metadata, 'out', topup_wf, 'inputspec.bold_epi_metadata')
                wf.connect(inputspec, 'bold_epi_metadata', run_wf, 'select_bold_epi_metadata_%s.inlist' % ix)

                select_epi_op_metadata = pe.Node(niu.Select(index=ix), 
                                          name='select_epi_op_metadata_%s' % ix)
                run_wf.connect(select_epi_op_metadata, 'out', topup_wf, 'inputspec.epi_op_metadata')
                wf.connect(inputspec, 'epi_op_metadata', run_wf, 'select_epi_op_metadata_%s.inlist' % ix)


                if type(init_reg_file) is list:
                    registration_wf = create_epi_to_T1_workflow(package=epi_to_t1_package,
                                                                parameter_file=linear_registration_parameters,
                                                                init_reg_file=init_reg_file[ix],
                                                                dof=dof,
                                                                cost_func=cost_func,
                                                                num_threads_ants=num_threads_ants)
                else:
                    registration_wf = create_epi_to_T1_workflow(package=epi_to_t1_package,
                                                                parameter_file=linear_registration_parameters,
                                                                init_reg_file=init_reg_file,
                                                                dof=dof,
                                                                cost_func=cost_func,
                                                                num_threads_ants=num_threads_ants)

                wf.connect(inputspec, 'wm_seg', registration_wf, 'inputspec.wm_seg_file')
                run_wf.connect(topup_wf, 'outputspec.bold_epi_corrected', registration_wf, 'inputspec.EPI_space_file')
                wf.connect(inputspec, 'T1w', run_wf, 'epi_to_T1.inputspec.T1_file')

                    
                ix1 = ix + 1

                wf.connect(run_wf, 'bids_topup_workflow.outputspec.bold_epi_unwarp_field', \
                           merge_topup_corrections_runs, 'in%s' % ix1)

                wf.connect(run_wf, 'epi_to_T1.outputspec.EPI_T1_matrix_file', \
                           merge_epi_to_T1w_transforms_runs, 'in%s' % ix1)

                wf.connect(run_wf, 'applymask_bold_epi.out_file', \
                           merge_mean_epis, 'in%s' % ix1)

                wf.connect(run_wf, 'mc_wf_bold_epi.outputspec.motion_corrected_files', \
                           merge_mc_epis, 'in%s' % ix1)

                wf.connect(run_wf, 'mc_wf_bold_epi.outputspec.EPI_space_mask', \
                           merge_epi_masks, 'in%s' % ix1)


            merge_bold_epi_to_T1w = pe.MapNode(niu.Merge(2),
                                               iterfield=['in1', 'in2'],
                                               name='merge_bold_epi_to_T1w')
            transform_epi_to_T1w_no_within_epi_reg = pe.MapNode(ants.ApplyTransforms(dimension=3,
                                                                float=True,
                                                                 num_threads=num_threads_ants,
                                                                interpolation='LanczosWindowedSinc'),
                                              iterfield=['input_image',
                                                         'transforms'],
                                              name='transform_epi_to_T1w_no_within_epi_reg')
            
            wf.connect(merge_epi_to_T1w_transforms_runs, 'out', merge_bold_epi_to_T1w, 'in1')
            wf.connect(merge_topup_corrections_runs, 'out', merge_bold_epi_to_T1w, 'in2')

            transform_epi_to_T1w = pe.MapNode(ants.ApplyTransforms(dimension=3,
                                                                float=True,
                                                                   num_threads=num_threads_ants,
                                                                interpolation='LanczosWindowedSinc'),
                                              iterfield=['input_image', 'transforms'],
                                              name='transform_epi_to_T1w')

            wf.connect(merge_mean_epis, 'out', transform_epi_to_T1w, 'input_image')
            wf.connect(inputspec, 'T1w', transform_epi_to_T1w, 'reference_image')
            wf.connect(merge_bold_epi_to_T1w, 'out', transform_epi_to_T1w, 'transforms')


            wf.connect(merge_mc_epis, 'out', pre_outputnode, 'bold_epi_mc')
            wf.connect(merge_epi_masks, 'out', pre_outputnode, 'bold_epi_mask')
            wf.connect(merge_mean_epis, 'out', pre_outputnode, 'bold_epi_mean')
            wf.connect(merge_bold_epi_to_T1w, 'out', pre_outputnode, 'bold_epi_to_T1w_transforms')
            wf.connect(transform_epi_to_T1w, 'output_image', pre_outputnode, 'mean_epi_in_T1w_space')

    
    elif method == 't1w_epi':


        t1w_epi_wf = create_t1w_epi_registration_workflow(linear_registration_parameters=linear_registration_parameters,
                                                          nonlinear_registration_parameters=nonlinear_registration_parameters,
                                                          num_threads_ants=num_threads_ants,
                                                          init_reg_file=init_reg_file)

        wf.connect(inputspec, 'inv2_epi',  t1w_epi_wf, 'inputspec.INV2_epi')
        wf.connect(inputspec, 'T1w',  t1w_epi_wf, 'inputspec.T1w')
        wf.connect(inputspec, 'T1w_epi',  t1w_epi_wf, 'inputspec.T1w_epi')
        wf.connect(inputspec, 'bold_epi',  t1w_epi_wf, 'inputspec.bold_epi')
        

        wf.connect(t1w_epi_wf, 'outputspec.bold_epi_mc',  pre_outputnode, 'bold_epi_mc')
        wf.connect(t1w_epi_wf, 'outputspec.bold_epi_mask',  pre_outputnode, 'bold_epi_mask')
        wf.connect(t1w_epi_wf, 'outputspec.bold_epi_mean',  pre_outputnode, 'bold_epi_mean')
        wf.connect(t1w_epi_wf, 'outputspec.bold_epi_to_T1w_transforms', pre_outputnode, 'bold_epi_to_T1w_transforms')
        wf.connect(t1w_epi_wf, 'outputspec.bold_epi_to_T1w_transformed', pre_outputnode, 'mean_epi_in_T1w_space')


    outputspec = pe.Node(niu.IdentityInterface(fields=out_fields),
                         name='outputspec')

    wf.connect(pre_outputnode, 'bold_epi_mc', outputspec, 'bold_epi_mc')
    wf.connect(pre_outputnode, 'bold_epi_mean', outputspec, 'bold_epi_mean')
    wf.connect(pre_outputnode, 'bold_epi_mask', outputspec, 'bold_epi_mask')

    if within_epi_reg or polish:

        pre_outputnode2 = pe.Node(niu.IdentityInterface(fields=['bold_epi_to_T1w_transforms', 'mean_epi_in_T1w_space']),
                               name='pre_outputnode2')

        pre_outputnode3 = pe.Node(niu.IdentityInterface(fields=['bold_epi_to_T1w_transforms', 'mean_epi_in_T1w_space']),
                               name='pre_outputnode3')

        if within_epi_reg:
            within_epi_reg_wf = create_within_epi_reg_EPI_registrations_wf(initial_transforms=True)

            wf.connect(inputspec, 'T1w', within_epi_reg_wf, 'inputspec.T1w')
            wf.connect(pre_outputnode, 'bold_epi_mean', within_epi_reg_wf, 'inputspec.bold_epi')

            # COMPOSE COMPOSITE TRANSFORM
            compose_epi_to_t1w_transform = pe.Node(ComposeMultiTransform(dimension=3), name='compose_epi_to_t1w_transform')
            wf.connect(pre_outputnode, 'bold_epi_to_T1w_transforms', compose_epi_to_t1w_transform, 'transforms')
            wf.connect(pre_outputnode, 'mean_epi_in_T1w_space', compose_epi_to_t1w_transform, 'reference_image')
            wf.connect(compose_epi_to_t1w_transform, 'output_transform', within_epi_reg_wf, 'inputspec.initial_transforms')

            wf.connect(within_epi_reg_wf, 'outputspec.bold_epi_to_T1w_transforms', pre_outputnode2, 'bold_epi_to_T1w_transforms')
            wf.connect(within_epi_reg_wf, 'outputspec.mean_epi_in_T1w_space', pre_outputnode2, 'mean_epi_in_T1w_space')

        else:
            wf.connect(pre_outputnode, 'outputspec.bold_epi_to_T1w_transforms', pre_outputnode2, 'bold_epi_to_T1w_transforms')
            wf.connect(pre_outputnode, 'outputspec.mean_epi_in_T1w_space', pre_outputnode2, 'mean_epi_in_T1w_space')
        
        if polish:
            polish_wf = polish_bold_epi_runs_in_T1w_space()

            wf.connect(inputspec, 'T1w', polish_wf, 'inputspec.T1w')
            wf.connect(pre_outputnode, 'bold_epi_mean', polish_wf, 'inputspec.bold_epi')

            compose_epi_to_t1w_transform2 = pe.Node(ComposeMultiTransform(dimension=3), name='compose_epi_to_t1w_transform2')
            wf.connect(pre_outputnode2, 'bold_epi_to_T1w_transforms', compose_epi_to_t1w_transform2, 'transforms')
            wf.connect(pre_outputnode, 'mean_epi_in_T1w_space', compose_epi_to_t1w_transform2, 'reference_image')

            wf.connect(compose_epi_to_t1w_transform2, 'output_transform', polish_wf, 'inputspec.initial_transforms')
            wf.connect(polish_wf, 'outputspec.bold_epi_to_T1w_transforms', pre_outputnode3, 'bold_epi_to_T1w_transforms')
            wf.connect(polish_wf, 'outputspec.mean_epi_in_T1w_space', pre_outputnode3, 'mean_epi_in_T1w_space')
        else:
            wf.connect(pre_outputnode2, 'bold_epi_to_T1w_transforms', pre_outputnode3, 'bold_epi_to_T1w_transforms')
            wf.connect(pre_outputnode2, 'mean_epi_in_T1w_space', pre_outputnode3, 'mean_epi_in_T1w_space')

        wf.connect(pre_outputnode3, 'bold_epi_to_T1w_transforms', outputspec, 'bold_epi_to_T1w_transforms')
        wf.connect(pre_outputnode3, 'mean_epi_in_T1w_space', outputspec, 'mean_epi_in_T1w_space')

    else:
        for field in out_fields[3:]:
            wf.connect(pre_outputnode, field, outputspec, field)
            
    return wf

def create_within_epi_reg_EPI_registrations_wf(method='best-run',
                                          epi_runs=None,
                                          apply_transform=False,
                                          initial_transforms=None,
                                          num_threads_ants=4,
                                          linear_registration_parameters='linear_hires.json'):
    """ Given a set of EPI runs registered to a
    T1w-image. Register the EPI runs to each other, to maximize overlap.
    The EPI that has the highest Mutual Information with the T1-weighted image is
    """
    import numpy as np

    if method != 'best-run':
        raise NotImplementedError('Nope.')
    
    in_fields = ['bold_epi', 'T1w', 'initial_transforms']

    inputspec = pe.Node(niu.IdentityInterface(fields=in_fields),
                        name='inputspec')

    if epi_runs:
        inputspec.inputs.bold_epi = epi_runs

    wf = pe.Workflow(name='within_epi_reg_registration')

    mean_epis = pe.Node(niu.Function(function=average_over_runs),
                         name='mean_epis')

    epi_masker = pe.Node(afni.Automask(outputtype='NIFTI_GZ'),
                        name='epi_masker')

    measure_similarity = pe.MapNode(ants.MeasureImageSimilarity(metric='MI',
                                                                dimension=3,
                                                                metric_weight=1.0,
                                                                radius_or_number_of_bins=5,
                                                                sampling_strategy='Regular',
                                                                num_threads=num_threads_ants,
                                                                sampling_percentage=1.0),
                                    iterfield=['moving_image'],
                                    name='measure_similarity')

    bold_registration_json = pkg_resources.resource_filename('spynoza.data.ants_json', linear_registration_parameters)

    select_reference_epi = pe.Node(niu.Select(),
                                   name='select_reference_epi')

    outputspec = pe.Node(niu.IdentityInterface(fields=['mean_epi_in_T1w_space',
                                                       'bold_epi_to_T1w_transforms']),
                         name='outputspec')

    if initial_transforms:
        inputspec.inputs.initial_transforms = initial_transforms

        ants_registration = pe.MapNode(ants.Registration(from_file=bold_registration_json,
                                                         num_threads=4,
                                                  output_warped_image=apply_transform), 
                                   iterfield=['moving_image',
                                              'initial_moving_transform'],
                                name='ants_registration')
        transform_inputs = pe.MapNode(ants.ApplyTransforms(num_threads=num_threads_ants),
                                     iterfield=['input_image',
                                                'transforms'],
                                     name='transform_input')
        wf.connect(inputspec, 'initial_transforms', transform_inputs, 'transforms')
        wf.connect(inputspec, 'bold_epi', transform_inputs, 'input_image')
        wf.connect(inputspec, 'T1w', transform_inputs, 'reference_image')
        wf.connect(transform_inputs, 'output_image', mean_epis, 'in_files')
        wf.connect(transform_inputs, 'output_image', measure_similarity, 'moving_image')
        wf.connect(inputspec, 'initial_transforms', ants_registration, 'initial_moving_transform')

        wf.connect(transform_inputs, 'output_image', select_reference_epi, 'inlist')
        wf.connect(select_reference_epi, ('out', pickfirst), ants_registration, 'fixed_image')

    else:
        ants_registration = pe.MapNode(ants.Registration(from_file=bold_registration_json,
                                                         num_threads=num_threads_ants,
                                                  output_warped_image=apply_transform), 
                                   iterfield=['moving_image'],
                                name='ants_registration')
        wf.connect(inputspec, 'bold_epi', select_reference_epi, 'inlist')
        wf.connect(inputspec, 'bold_epi', mean_epis, 'in_files')
        wf.connect(inputspec, 'bold_epi', measure_similarity, 'moving_image')
        wf.connect(select_reference_epi, ('out', pickfirst), ants_registration, 'fixed_image')


    wf.connect(mean_epis, 'out', epi_masker, 'in_file')
    wf.connect(epi_masker, 'out_file', measure_similarity, 'fixed_image_mask')
    wf.connect(inputspec, 'T1w', measure_similarity, 'fixed_image')

    wf.connect(measure_similarity, ('similarity', argmax), select_reference_epi, 'index')

    wf.connect(epi_masker, 'out_file', ants_registration, 'fixed_image_masks')
    wf.connect(inputspec, 'bold_epi', ants_registration, 'moving_image')

    wf.connect(ants_registration, 'warped_image', outputspec, 'mean_epi_in_T1w_space')
    wf.connect(ants_registration, 'forward_transforms', outputspec, 'bold_epi_to_T1w_transforms')

    return wf

def polish_bold_epi_runs_in_T1w_space(name='polish_bold_epi_in_T1w_space',
                                      mean_bold_epis=None,
                                      T1w=None,
                                      num_threads_ants=4,
                                      initial_moving_transforms=None,
                                      registration_parameters='nonlinear_precise.json'):
    """ Assumes that after mean_bold_epis are transformed using initial_transforms,
        they are approximately exactly overlapping """

    wf = pe.Workflow(name=name)

    inputspec = pe.Node(niu.IdentityInterface(fields=['initial_transforms',
                                                      'T1w',
                                                      'bold_epi']),
                        name='inputspec')

    if mean_bold_epis:
        inputspec.inputs.bold_epi = mean_bold_epis

    if T1w:
        inputspec.inputs.T1w = T1w

    if initial_moving_transforms:
        inputspec.inputs.initial_transforms = initial_moving_transforms



    transform_inputs = pe.MapNode(ants.ApplyTransforms(num_threads=num_threads_ants),
                                 iterfield=['input_image',
                                            'transforms'],
                                 name='transform_input')

    wf.connect(inputspec, 'bold_epi', transform_inputs, 'input_image')
    wf.connect(inputspec, 'T1w', transform_inputs, 'reference_image')
    wf.connect(inputspec, ('initial_transforms', reverse), transform_inputs, 'transforms')

    mean_runs = pe.Node(niu.Function(function=average_over_runs),
                        name='mean_runs')
    wf.connect(transform_inputs, 'output_image', mean_runs, 'in_files')

    registration_json = pkg_resources.resource_filename('spynoza.data.ants_json', registration_parameters)
    ants_registration = pe.Node(ants.Registration(from_file=registration_json, 
                                                  num_threads=num_threads_ants,
                                                  output_warped_image=True), 
                            name='ants_registration')

    wf.connect(mean_runs, 'out', ants_registration, 'moving_image')
    wf.connect(inputspec, 'T1w', ants_registration, 'fixed_image')

    merge_transforms = pe.MapNode(niu.Merge(2),
                                  iterfield=['in1'],
                                  name='merge_transforms')

    wf.connect(inputspec, 'initial_transforms',  merge_transforms, 'in1')
    wf.connect(ants_registration, 'forward_transforms',  merge_transforms, 'in2')

    transform_outputs = pe.MapNode(ants.ApplyTransforms(num_threads=num_threads_ants),
                                   iterfield=['input_image',
                                              'transforms'],
                                   name='transform_outputs')

    wf.connect(inputspec, 'bold_epi', transform_outputs, 'input_image')
    wf.connect(inputspec, 'T1w', transform_outputs, 'reference_image')
    wf.connect(merge_transforms, ('out', reverse), transform_outputs, 'transforms')


    out_fields = ['mean_epi_in_T1w_space', 'bold_epi_to_T1w_transforms']
    outputspec = pe.Node(niu.IdentityInterface(fields=out_fields),
                         name='outputspec')
    wf.connect(transform_outputs, 'output_image', outputspec, 'mean_epi_in_T1w_space')
    wf.connect(merge_transforms, 'out', outputspec, 'bold_epi_to_T1w_transforms')

    return wf


def _make_list_from_element(element, template_list):
    return [element] * len(template_list)


def argmax(in_values):
    import numpy as np
    return np.argmax(in_values)

def reverse(in_values):
    return in_values[::-1]

