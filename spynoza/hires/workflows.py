import nipype.pipeline.engine as pe
import nipype.interfaces.utility as niu
from nipype.interfaces import fsl, ants, afni
from nipype.interfaces.base import isdefined
import pkg_resources

from ..utils import average_over_runs, get_scaninfo, init_temporally_crop_run_wf, pickfirst, crop_anat_and_bold
from ..filtering.nodes import savgol_filter

from ..motion_correction.workflows import create_motion_correction_workflow
from ..unwarping.topup.workflows import create_topup_workflow
from ..unwarping.t1w_epi.workflows import create_t1w_epi_registration_workflow
from ..registration.sub_workflows import create_epi_to_T1_workflow
from ..conversion.nodes import percent_signal_change

from spynoza.io.bids_interfaces import collect_data

from niworkflows.interfaces.utils import CopyXForm

from nipype.interfaces.ants.utils import ComposeMultiTransform
from niworkflows.interfaces import SimpleBeforeAfter
from fmriprep.interfaces import MultiApplyTransforms, DerivativesDataSink
from fmriprep.interfaces.nilearn import Merge as MergeImages

def init_hires_unwarping_wf(name="unwarp_hires",
                            method='topup',
                            bids_layout=None,
                            derivatives_dir='/derivatives',
                            single_warpfield=False,
                            register_to='last',
                            init_transform=None,
                            linear_registration_parameters='linear_hires.json',
                            nonlinear_registration_parameters='nonlinear_precise.json',
                            bold=None,
                            epi_op=None,
                            t1w_epi=None,
                            t1w=None,
                            dura_mask=None,
                            wm_seg=None,
                            cost_func=None,
                            inv2_epi=None,
                            dof=6,
                            crop_bolds=True,
                            topup_package='afni',
                            epi_to_t1_package='ants',
                            within_epi_reg=True,
                            polish=True,
                            omp_nthreads=4,
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
    bold : list:
        List of BOLD EPI runs.
    epi_op : list/filename:
        List of EPI runs with opposite-phase encoding. Should be same length as and
        corresponding to bold.
    crop_epi : bool
        Whether or not to crop the BOLD EPIs to the size of their corresponding
        EPI_op.
    t1w : filename
        T1-weighted structural image
    dura_mask : filename, optional
        Mask of dura
    wm_seg : bool
        whether to use wm_seg
    cost_func : 'mutualinfo', 'bbr', or 'corratio'...
        Cost funtion to use for FSL. By default uses BBR, when wm_seg is given,
        otherwise mutualinfo
    t1w_epi : list/filename
        T1-weighted EPI with same distortions as bold.
        
    """


    wf = pe.Workflow(name=name)
    
    fields = ['bold', 'T1w', 'wm_seg', 'dura_mask']
    
    if method == 'topup':
        fields += ['epi_op',
                   'bold_metadata',
                   'epi_op_metadata']
    elif method == 't1w_epi':
        fields += ['T1w_epi', 'inv2_epi']
    
    inputspec = pe.Node(niu.IdentityInterface(fields=fields),
                        name='inputspec')

    if within_epi_reg and single_warpfield:
        raise Exception('You cannot use a single warpfield and register within!')
    
    if bold:
        inputspec.inputs.bold = bold
        if bids_layout:
            inputspec.inputs.bold_metadata = [bids_layout.get_metadata(epi) for epi in bold]
        
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

    if dura_mask:
        inputspec.inputs.dura_mask = dura_mask

    if wm_seg:
        cost_func = 'bbr'
    else:
        cost_func = 'mutualinfo'
            
    out_fields = ['bold_mc',
                  'bold_mask',
                  'bold_mean',
                  'bold_to_T1w_transforms',
                  'mean_epi_in_T1w_space']
    
    pre_outputnode = pe.Node(niu.IdentityInterface(fields=out_fields),
                             name='pre_outputnode')

    
    #  *** TOPUP ***
    if method == 'topup':
        
        if dura_mask:
            dura_masker = pe.Node(fsl.ApplyMask(), name='dura_masker')
            wf.connect(inputspec, 'T1w', dura_masker, 'in_file')

            mask_inverter = pe.Node(niu.Function(function=invert_mask,
                                               input_names=['mask_file'],
                                               output_names=['mask_inv']),
                                  name='invert_mask')
            wf.connect(inputspec, 'dura_mask', mask_inverter, 'mask_file')
            wf.connect(mask_inverter, 'mask_inv', dura_masker, 'mask_file')
        # *** only ONE warpfield ***
        if single_warpfield:

            correct_wf = create_pepolar_reg_wf('unwarp_reg_wf',
                                               dof=dof,
                                               registration_parameters=linear_registration_parameters)

            correct_wf.inputs.inputnode.init_transform = init_transform

            print(inputspec.inputs)

            wf.connect(inputspec, 'bold', correct_wf, 'inputnode.bold')
            wf.connect(inputspec, 'epi_op', correct_wf, 'inputnode.epi_op')
            wf.connect(inputspec, ('bold_metadata', pickfirst), correct_wf, 'inputnode.bold_metadata')
            wf.connect(inputspec, 'wm_seg', correct_wf, 'inputnode.wm_seg')

            if dura_mask:
                wf.connect(dura_masker, 'out_file', correct_wf, 'inputnode.T1w')
            else:
                wf.connect(inputspec, 'T1w', correct_wf, 'inputnode.T1w')

        # SEPERATE warpfields for each run
        else:


            if not (isdefined(inputspec.inputs.bold) and isdefined(inputspec.inputs.epi_op)):
                    raise Exception ("When using separate warpfield, bold and epi_op" \
                                    " have to be defined at workflow initialization")
            
            if not (len(inputspec.inputs.bold) == len(inputspec.inputs.epi_op)):
                raise Exception ("Number of bold and epi_op runs should be identical")
            
            merge_ref_bold = pe.Node(niu.Merge(len(bold)),
                                               name='merge_ref_bold')
            merge_ref_mask = pe.Node(niu.Merge(len(bold)),
                                               name='merge_ref_mask')
            merge_bold_to_t1w_linear = pe.Node(niu.Merge(len(bold)),
                                               name='merge_bold_to_t1w_linear')
            merge_unwarp_field = pe.Node(niu.Merge(len(bold)),
                                               name='merge_unwarp_field')
            merge_hmc_itk = pe.Node(niu.Merge(len(bold)),
                                               name='merge_hmc_itk')

            for ix in range(len(epi_op)):

                select_bold = pe.Node(niu.Select(index=ix), 
                                          name='select_bold_%s' % ix)
                select_epi_op = pe.Node(niu.Select(index=ix), 
                                          name='select_epi_op_%s' % ix)
                select_bold_metadata = pe.Node(niu.Select(index=ix), 
                                          name='select_bold_metadata_%s' % ix)

                correct_wf = create_pepolar_reg_wf('unwarp_reg_wf_{}'.format(ix),
                                                   dof=dof,
                                                   registration_parameters=linear_registration_parameters)
                correct_wf.inputs.inputnode.init_transform = init_transform

                wf.connect(inputspec, 'bold', select_bold, 'inlist')
                wf.connect(inputspec, 'epi_op', select_epi_op, 'inlist')

                wf.connect(inputspec, 'bold_metadata', select_bold_metadata, 'inlist')

                wf.connect(select_bold, 'out', correct_wf, 'inputnode.bold')
                wf.connect(select_epi_op, 'out', correct_wf, 'inputnode.epi_op')
                wf.connect(select_bold_metadata, 'out', correct_wf, 'inputnode.bold_metadata')

                wf.connect(inputspec, 'wm_seg', correct_wf, 'inputnode.wm_seg')

                if dura_mask:
                    wf.connect(dura_masker, 'out_file', correct_wf, 'inputnode.T1w')

                else:
                    wf.connect(inputspec, 'T1w', correct_wf, 'inputnode.T1w')

                wf.connect(correct_wf, 'outputnode.ref_bold', merge_ref_bold, 'in{}'.format(ix+1))
                wf.connect(correct_wf, 'outputnode.bold_to_t1w_linear', merge_bold_to_t1w_linear, 'in{}'.format(ix+1))
                wf.connect(correct_wf, 'outputnode.unwarp_field', merge_unwarp_field, 'in{}'.format(ix+1))
                wf.connect(correct_wf, 'outputnode.hmc_itk', merge_hmc_itk, 'in{}'.format(ix+1))
                wf.connect(correct_wf, 'outputnode.ref_mask', merge_ref_mask, 'in{}'.format(ix+1))

            if within_epi_reg:
                within_epi_wf = init_within_epi_reg_EPI_registrations_wf()

                wf.connect(merge_ref_bold, 'out', within_epi_wf, 'inputnode.ref_bold')

                if dura_mask:
                    wf.connect(dura_masker, 'out_file', within_epi_wf, 'inputnode.T1w')

                else:
                    wf.connect(inputspec, 'T1w', within_epi_wf, 'inputnode.T1w')
                
                merge_transforms1 = pe.MapNode(niu.Merge(2),
                                               iterfield=['in1', 'in2'],
                                            name='merge_transforms1')

                wf.connect(merge_bold_to_t1w_linear, 'out', merge_transforms1, 'in1')
                wf.connect(merge_unwarp_field, 'out', merge_transforms1, 'in2')
                wf.connect(merge_transforms1, 'out', within_epi_wf, 'inputnode.init_transforms')

            

        # RESAMPLE ORIGINAL BOLD
        resample_wf = init_resample_wf(omp_nthreads=omp_nthreads,
                                       derivatives_dir=derivatives_dir)

        if within_epi_reg:
            wf.connect(merge_ref_bold, 'out', resample_wf, 'inputnode.ref_bold')
            wf.connect(merge_ref_mask, 'out', resample_wf, 'inputnode.ref_mask')

            combine_transforms = pe.MapNode(niu.Merge(4), 
                                            iterfield=['in1', 'in2', 'in3', 'in4'],
                                            name='combine_transforms')

            wf.connect(merge_hmc_itk, 'out', combine_transforms, 'in1')
            wf.connect(merge_bold_to_t1w_linear, 'out', combine_transforms, 'in3')
            wf.connect(merge_unwarp_field, 'out', combine_transforms, 'in2')

            pick_final_transforms = pe.MapNode(niu.Function(function=pick_from,
                                                         input_names=['in_list', 'n'],
                                                          output_names=['out_list']),
                                               iterfield=['in_list'],
                                            name='pick_final_transforms')
            pick_final_transforms.inputs.n = 2
            wf.connect(within_epi_wf, 'outputnode.bold_to_T1w_transforms', pick_final_transforms, 'in_list')
            wf.connect(pick_final_transforms, 'out_list', combine_transforms, 'in4')

        else:
            wf.connect(correct_wf, 'outputnode.ref_bold', resample_wf, 'inputnode.ref_bold')
            wf.connect(correct_wf, 'outputnode.ref_mask', resample_wf, 'inputnode.ref_mask')

            combine_transforms = pe.MapNode(niu.Merge(3), 
                                            iterfield=['in1'],
                                            name='combine_transforms')
            wf.connect(correct_wf, 'outputnode.hmc_itk', combine_transforms, 'in1')
            wf.connect(correct_wf, 'outputnode.unwarp_field', combine_transforms, 'in2')
            wf.connect(correct_wf, 'outputnode.bold_to_t1w_linear', combine_transforms, 'in3')

        wf.connect(combine_transforms, 'out', resample_wf, 'inputnode.transforms')
        wf.connect(inputspec, 'bold', resample_wf, 'inputnode.bold')
        wf.connect(inputspec, 'bold_metadata', resample_wf, 'inputnode.bold_metadata')
        wf.connect(inputspec, 'T1w', resample_wf, 'inputnode.T1w')


    return wf


def create_pepolar_reg_wf(name='unwarp_and_reg_to_T1',
                          crop_bolds=True,
                          topup_package='afni',
                          epi_to_t1_package='fsl',
                          registration_parameters='linear_hires.json',
                          dof=6,
                          cost_func='bbr',
                          omp_nthreads=4):

    from fmriprep.interfaces import MCFLIRT2ITK
    from fmriprep.workflows.fieldmap import init_fmap_unwarp_report_wf

    wf = pe.Workflow(name=name)

    inputnode = pe.Node(niu.IdentityInterface(fields=['bold', 'epi_op', 
                                                      'bold_metadata',
                                                      'wm_seg', 'T1w',
                                                      'init_transform']),
                         name='inputnode')

    mc_wf_bold = create_motion_correction_workflow(name='mc_wf_bold',
                                                  output_mask=True,
                                                   return_mat_files=True,
                                                  method='FSL',
                                                  lightweight=True)

    wf.connect(inputnode, 'bold', mc_wf_bold, 'inputspec.in_files')
    wf.connect(inputnode, ('bold', pickfirst), mc_wf_bold, 'inputspec.which_file_is_EPI_space')
    mc_wf_bold.inputs.create_bold_mask.connected = False
    
    mcflirt_to_itk = pe.MapNode(MCFLIRT2ITK(), 
                                iterfield=['in_files'],
                                name='mcflirt_to_itk')

    wf.connect(inputnode, ('bold', pickfirst), mcflirt_to_itk, 'in_source')
    wf.connect(inputnode, ('bold', pickfirst), mcflirt_to_itk, 'in_reference')
    wf.connect(mc_wf_bold, 'outputspec.mat_files', mcflirt_to_itk, 'in_files')

    mc_wf_epi_op = create_motion_correction_workflow(name='mc_wf_epi_ops',
                                                     method='FSL',
                                                     output_mask=True,
                                                     lightweight=True)
    mc_wf_epi_op.inputs.create_bold_mask.connected=False

    wf.connect(inputnode, 'epi_op', mc_wf_epi_op, 'inputspec.in_files')
    wf.connect(inputnode, ('epi_op', pickfirst), mc_wf_epi_op, 'inputspec.which_file_is_EPI_space')
        
    mean_bold1 = pe.MapNode(fsl.MeanImage(dimension='T'), 
                                 iterfield=['in_file'],
                                 name='mean_bold1')

    if crop_bolds:
        crop_bold_wf = init_temporally_crop_run_wf(name='crop_wf')
        wf.connect(mc_wf_bold, 'outputspec.motion_corrected_files', crop_bold_wf, 'inputspec.in_files')
        wf.connect(inputnode, 'epi_op', crop_bold_wf, 'inputspec.templates')
        wf.connect(crop_bold_wf, 'outputspec.out_files', mean_bold1, 'in_file')
    else:
        wf.connect(mc_wf_bold, 'outputspec.motion_corrected_files', mean_bold1, 'in_file')


    biasfield_correct_bold = pe.Node(ants.N4BiasFieldCorrection(
                                    dimension=3, copy_header=True),
                                         name='biasfield_correct_bold')

    mean_bold2 = pe.Node(niu.Function(function=average_over_runs,
                                      input_names=['in_files'],
                                      output_names=['out_file']),
                         name='mean_bold2')

    wf.connect(mean_bold1, 'out_file', mean_bold2, 'in_files')
    wf.connect(mean_bold2, 'out_file', biasfield_correct_bold, 'input_image') 

    applymask_bold = pe.Node(fsl.ApplyMask(),
                                    name="applymask_bold")

    wf.connect(biasfield_correct_bold, 'output_image', applymask_bold, 'in_file') 
    wf.connect(mc_wf_bold, 'outputspec.EPI_space_mask', applymask_bold, 'mask_file') 


    mean_epi_op1 = pe.MapNode(fsl.MeanImage(dimension='T'), 
                                 iterfield=['in_file'],
                                 name='mean_epi_op1')

    wf.connect(mc_wf_epi_op, 'outputspec.motion_corrected_files', mean_epi_op1, 'in_file') 

    mean_epi_op2 = pe.Node(niu.Function(function=average_over_runs,
                                      input_names=['in_files'],
                                      output_names=['out_file']),
                         name='mean_epi_op2')

    wf.connect(mean_epi_op1, 'out_file', mean_epi_op2, 'in_files')

    biasfield_correct_epi_op = pe.Node(ants.N4BiasFieldCorrection(
                                  dimension=3, copy_header=True),
                                         name='biasfield_correct_epi_op')

    wf.connect(mean_epi_op2, 'out_file', biasfield_correct_epi_op, 'input_image') 

    applymask_epi_op = pe.Node(fsl.ApplyMask(), name="applymask_epi_op")
    wf.connect(biasfield_correct_epi_op, 'output_image', applymask_epi_op, 'in_file') 
    wf.connect(mc_wf_epi_op, 'outputspec.EPI_space_mask', applymask_epi_op, 'mask_file') 

    topup_wf = create_topup_workflow(package=topup_package,
                                          omp_nthreads=omp_nthreads)
    topup_wf.get_node('qwarp').inputs.minpatch = 5

    wf.connect(applymask_bold, 'out_file', topup_wf, 'inputspec.bold')
    wf.connect(applymask_epi_op, 'out_file', topup_wf, 'inputspec.epi_op')

    wf.connect(inputnode, 'bold_metadata', topup_wf, 'inputspec.bold_metadata')


    registration_wf = create_epi_to_T1_workflow(name='epi_to_T1',
                                                package=epi_to_t1_package,
                                                parameter_file=registration_parameters,
                                                dof=dof,
                                                cost_func=cost_func)

    wf.connect(inputnode, 'wm_seg', registration_wf, 'inputspec.wm_seg_file')
    wf.connect(topup_wf, 'outputspec.bold_corrected', registration_wf, 'inputspec.EPI_space_file')
    wf.connect(inputnode, 'T1w', registration_wf, 'inputspec.T1_file')
    wf.connect(inputnode, 'init_transform', registration_wf, 'inputspec.init_transform')


    #  MERGE TRANSFORMS
    merge_transforms = pe.Node(niu.Merge(2), name='merge_transforms')
    wf.connect(topup_wf, 'outputspec.bold_unwarp_field', merge_transforms, 'in1')
    wf.connect(registration_wf, 'outputspec.EPI_T1_matrix_file', merge_transforms, 'in2')

    # TRANSFORM UNWARPED BOLD
    transform_bold_to_T1w = pe.MapNode(ants.ApplyTransforms(dimension=3,
                                                        float=True,
                                                        num_threads=omp_nthreads,
                                                        interpolation='LanczosWindowedSinc'),
                                      iterfield=['input_image'],
                                      name='transform_bold_to_T1w')

    wf.connect(applymask_bold, 'out_file', transform_bold_to_T1w, 'input_image')
    wf.connect(inputnode, 'T1w', transform_bold_to_T1w, 'reference_image')
    wf.connect(merge_transforms, ('out', reverse), transform_bold_to_T1w, 'transforms')
    
    # REPORT ON PEPOLAR UNWARP
    report_unwarp_wf = init_fmap_report_wf()
    wf.connect(applymask_bold, 'out_file', report_unwarp_wf, 'inputnode.in_pre')
    wf.connect(topup_wf, 'outputspec.bold_corrected', report_unwarp_wf, 'inputnode.in_post')

    # Fmriprep wf expects something like dtissue
    wf.connect(inputnode, 'wm_seg', report_unwarp_wf, 'inputnode.wm_seg')
    wf.connect(registration_wf, 'outputspec.T1_EPI_matrix_file', report_unwarp_wf, 'inputnode.T1w_to_epi_xfm')


    # REPORT ON REGISTRATION
    report_reg_wf = init_crop_and_report_registration_wf()
    wf.connect(transform_bold_to_T1w, 'output_image', report_reg_wf, 'inputnode.bold')
    wf.connect(inputnode, 'T1w', report_reg_wf, 'inputnode.anat')
    wf.connect(inputnode, 'wm_seg', report_reg_wf, 'inputnode.wm_seg')
    
    # OUTPUTNODE
    outputnode = pe.Node(niu.IdentityInterface(fields=['unwarp_field',
                                                       'bold_to_t1w_linear',
                                                       'hmc_itk',
                                                       'unwarp_report',
                                                       'registration_report',
                                                       'ref_bold',
                                                       'ref_mask']),
                         name='outputnode')


    wf.connect(topup_wf, 'outputspec.bold_unwarp_field', outputnode, 'unwarp_field')
    wf.connect(registration_wf, 'outputspec.EPI_T1_matrix_file', outputnode, 'bold_to_t1w_linear')
    wf.connect(report_unwarp_wf, 'outputnode.unwarp_rpt', outputnode, 'unwarp_report')
    wf.connect(report_reg_wf, 'outputnode.reg_rpt', outputnode, 'registration_report')
    wf.connect(applymask_bold, 'out_file', outputnode, 'ref_bold')
    wf.connect(mcflirt_to_itk, 'out_file', outputnode, 'hmc_itk')
    wf.connect(mc_wf_bold, 'outputspec.EPI_space_mask', outputnode, 'ref_mask') 

    return wf

def init_crop_and_report_registration_wf(name='crop_and_report'):
    from niworkflows.interfaces import SimpleBeforeAfter

    wf = pe.Workflow(name=name)

    inputnode = pe.Node(niu.IdentityInterface(fields=['bold',
                                                      'anat',
                                                      'wm_seg']),
                        name='inputnode')

    crop_anat = pe.MapNode(niu.Function(function=crop_anat_and_bold,
                                input_names=['bold', 'anat'],
                                output_names=['bold_cropped', 'anat_cropped']),
                           iterfield=['bold'],
                   name='crop_anat')
    wf.connect(inputnode, 'bold', crop_anat, 'bold')
    wf.connect(inputnode, 'anat', crop_anat, 'anat')

    crop_wm_seg = pe.Node(niu.Function(function=crop_anat_and_bold,
                                input_names=['bold', 'anat'],
                                output_names=['bold_cropped', 'anat_cropped']),
                   name='crop_wm_seg')
    wf.connect(inputnode, ('bold', pickfirst), crop_wm_seg, 'bold')
    wf.connect(inputnode, 'wm_seg', crop_wm_seg, 'anat')


    reg_rpt = pe.MapNode(SimpleBeforeAfter(), 
                         iterfield=['before', 'after'],
                         name='reg_rpt', mem_gb=0.1)

    wf.connect(crop_anat, 'anat_cropped', reg_rpt, 'before')
    wf.connect(crop_anat, 'bold_cropped', reg_rpt, 'after')
    wf.connect(crop_wm_seg, 'anat_cropped', reg_rpt, 'wm_seg')

    outputnode = pe.Node(niu.IdentityInterface(fields=['reg_rpt']),
                         name='outputnode')

    wf.connect(reg_rpt, 'out_report', outputnode, 'reg_rpt')

    return wf

def init_fmap_report_wf(name='fmap_report'):

    wf = pe.Workflow(name=name)

    inputnode = pe.Node(niu.IdentityInterface(fields=['in_post',
                                                      'in_pre',
                                                      'wm_seg',
                                                      'T1w_to_epi_xfm']),
                        name='inputnode')

    
    transform_wm_seg = pe.Node(ants.ApplyTransforms(dimension=3, 
                                                    float=True, 
                                                    interpolation='MultiLabel'),
                               name='transform_wm_seg')
    
    unwarp_rpt = pe.MapNode(SimpleBeforeAfter(), 
                         iterfield=['before', 'after'],
                         name='unwarp_rpt', mem_gb=0.1)

    outputnode = pe.Node(niu.IdentityInterface(fields=['unwarp_rpt']),
                         name='outputnode')

    wf.connect([
        (inputnode, transform_wm_seg, [('wm_seg', 'input_image'),
                                       ('T1w_to_epi_xfm', 'transforms'),
                                       ('in_post', 'reference_image')]),
        (inputnode, unwarp_rpt, [('in_pre', 'before'),
                              ('in_post', 'after')]),
        (unwarp_rpt, outputnode, [('out_report', 'unwarp_rpt')])
    ])

    return wf


def init_within_epi_reg_EPI_registrations_wf(method='best-run',
                                              num_threads_ants=4,
                                              linear_registration_parameters='linear_hires.json'):
    """ Given a set of EPI runs registered to a
    T1w-image. Register the EPI runs to each other, to maximize overlap.
    The EPI that has the highest Mutual Information with the T1-weighted image is
    """
    import numpy as np

    if method != 'best-run':
        raise NotImplementedError('Nope.')
    
    in_fields = ['ref_bold', 'T1w', 'init_transforms']

    inputnode = pe.Node(niu.IdentityInterface(fields=in_fields),
                        name='inputnode')

    wf = pe.Workflow(name='within_epi_reg_registration')

    measure_similarity = pe.MapNode(ants.MeasureImageSimilarity(metric='MI',
                                                                dimension=3,
                                                                metric_weight=1.0,
                                                                radius_or_number_of_bins=25,
                                                                sampling_strategy='Regular',
                                                                num_threads=num_threads_ants,
                                                                sampling_percentage=1.0),
                                    iterfield=['moving_image'],
                                    name='measure_similarity')

    mean_epis = pe.Node(niu.Function(function=average_over_runs),
                                                 name='mean_epis')
    epi_masker = pe.Node(afni.Automask(outputtype='NIFTI_GZ'),
                                                 name='epi_masker')

    bold_registration_json = pkg_resources.resource_filename('spynoza.data.ants_json', linear_registration_parameters)

    select_reference_epi = pe.Node(niu.Select(),
                                   name='select_reference_epi')

    outputnode = pe.Node(niu.IdentityInterface(fields=['bold_to_T1w_transforms']),
                         name='outputnode')

    transform_inputs = pe.MapNode(ants.ApplyTransforms(num_threads=num_threads_ants),
                                 iterfield=['input_image',
                                            'transforms'],
                                 name='transform_input')

    ants_registration = pe.MapNode(ants.Registration(from_file=bold_registration_json,
                                                     num_threads=4,
                                                     write_composite_transform=False,
                                                     collapse_output_transforms=False,
                                              output_warped_image=True), 
                               iterfield=['moving_image',
                                          'initial_moving_transform'],
                            name='ants_registration')

    wf.connect(inputnode, 'init_transforms', transform_inputs, 'transforms')
    wf.connect(inputnode, 'ref_bold', transform_inputs, 'input_image')
    wf.connect(inputnode, 'T1w', transform_inputs, 'reference_image')

    wf.connect(transform_inputs, 'output_image', mean_epis, 'in_files')
    wf.connect(transform_inputs, 'output_image', measure_similarity, 'moving_image')

    wf.connect(inputnode, 'init_transforms', ants_registration, 'initial_moving_transform')

    wf.connect(transform_inputs, 'output_image', select_reference_epi, 'inlist')
    wf.connect(select_reference_epi, ('out', pickfirst), ants_registration, 'fixed_image')


    wf.connect(mean_epis, 'out', epi_masker, 'in_file')
    wf.connect(epi_masker, 'out_file', measure_similarity, 'fixed_image_mask')
    wf.connect(inputnode, 'T1w', measure_similarity, 'fixed_image')

    wf.connect(measure_similarity, ('similarity', argmin), select_reference_epi, 'index')

    wf.connect(epi_masker, 'out_file', ants_registration, 'fixed_image_masks')
    wf.connect(inputnode, 'ref_bold', ants_registration, 'moving_image')

    wf.connect(ants_registration, 'warped_image', outputnode, 'mean_epi_in_T1w_space')
    wf.connect(ants_registration, 'forward_transforms', outputnode, 'bold_to_T1w_transforms')

    return wf

def polish_bold_runs_in_T1w_space(name='polish_bold_in_T1w_space',
                                      mean_bolds=None,
                                      T1w=None,
                                      num_threads_ants=4,
                                      initial_moving_transforms=None,
                                      registration_parameters='nonlinear_precise.json'):
    """ Assumes that after mean_bolds are transformed using initial_transforms,
        they are approximately exactly overlapping """

    wf = pe.Workflow(name=name)

    inputspec = pe.Node(niu.IdentityInterface(fields=['initial_transforms',
                                                      'T1w',
                                                      'bold']),
                        name='inputspec')

    if mean_bolds:
        inputspec.inputs.bold = mean_bolds

    if T1w:
        inputspec.inputs.T1w = T1w

    if initial_moving_transforms:
        inputspec.inputs.initial_transforms = initial_moving_transforms



    transform_inputs = pe.MapNode(ants.ApplyTransforms(num_threads=num_threads_ants),
                                 iterfield=['input_image',
                                            'transforms'],
                                 name='transform_input')

    wf.connect(inputspec, 'bold', transform_inputs, 'input_image')
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

    wf.connect(inputspec, 'bold', transform_outputs, 'input_image')
    wf.connect(inputspec, 'T1w', transform_outputs, 'reference_image')
    wf.connect(merge_transforms, ('out', reverse), transform_outputs, 'transforms')


    out_fields = ['mean_epi_in_T1w_space', 'bold_to_T1w_transforms']
    outputspec = pe.Node(niu.IdentityInterface(fields=out_fields),
                         name='outputspec')
    wf.connect(transform_outputs, 'output_image', outputspec, 'mean_epi_in_T1w_space')
    wf.connect(merge_transforms, 'out', outputspec, 'bold_to_T1w_transforms')


    return wf

def init_resample_wf(name='resample_bold',
                     derivatives_dir='/derivatives',
                     highpass=True,
                     omp_nthreads=4):
    from niworkflows.interfaces.utils import GenerateSamplingReference


    wf = pe.Workflow(name=name)

    inputnode = pe.Node(niu.IdentityInterface(fields=['bold',
                                                      'ref_bold',
                                                      'ref_mask',
                                                      'transforms',
                                                      'bold_metadata',
                                                      'T1w']),
                        name='inputnode')

    reverse_transforms = pe.MapNode(niu.Function(function=reverse,
                                               input_names=['in_values'],
                                               output_names=['reverse_list']),
                                    iterfield=['in_values'],
                                    name='reverse_transforms')

    wf.connect(inputnode, 'transforms', reverse_transforms, 'in_values')

    split_bold = pe.MapNode(fsl.Split(dimension='t'),
                            iterfield='in_file',
                         name='split_bold')
    wf.connect(inputnode, 'bold', split_bold, 'in_file')

    transform_ref_mask = pe.Node(ants.ApplyTransforms(dimension=3, 
                                                         float=True, 
                                                         interpolation='MultiLabel'),
                               name='transform_ref_mask')

    wf.connect(inputnode, ('ref_mask', pickfirst), transform_ref_mask, 'input_image')
    wf.connect(inputnode, 'T1w', transform_ref_mask, 'reference_image')

    remove_hmc = pe.MapNode(niu.Function(function=pick_until,
                                      input_names=['in_list', 'n'],
                                      output_names=['out_list']),
                            iterfield=['in_list'],
                         name='remove_hmc')
    remove_hmc.inputs.n = -1

    wf.connect(reverse_transforms, 'reverse_list', remove_hmc, 'in_list')
    wf.connect(remove_hmc,  ('out_list', pickfirst), transform_ref_mask, 'transforms')



    crop_mask = pe.Node(niu.Function(function=crop_anat_and_bold,
                                input_names=['bold', 'anat'],
                                output_names=['bold_cropped', 'anat_cropped']),
                   name='crop_mask')
    wf.connect(transform_ref_mask,  'output_image', crop_mask, 'bold')
    wf.connect(inputnode,  'T1w', crop_mask, 'anat')

    gen_ref = pe.Node(GenerateSamplingReference(),
                      name='gen_ref')

    wf.connect(crop_mask, 'bold_cropped', gen_ref, 'fixed_image')
    wf.connect(inputnode, ('ref_bold', pickfirst), gen_ref, 'moving_image')

    transform_ref_mask2 = pe.Node(ants.ApplyTransforms(dimension=3, 
                                                         float=True, 
                                                         interpolation='MultiLabel'),
                               name='transform_ref_mask2')

    wf.connect(inputnode, ('ref_mask', pickfirst), transform_ref_mask2, 'input_image')
    wf.connect(gen_ref, 'out_file', transform_ref_mask2, 'reference_image')
    wf.connect(remove_hmc,  ('out_list', pickfirst), transform_ref_mask2, 'transforms')

    transform_bold_to_t1w = pe.MapNode(
                MultiApplyTransforms(interpolation="LanczosWindowedSinc", float=True, copy_dtype=True),
                iterfield=['input_image', 'transforms'],
                name='transform_bold_to_t1w', n_procs=omp_nthreads)

    wf.connect(split_bold, 'out_files', transform_bold_to_t1w, 'input_image')
    wf.connect(gen_ref, 'out_file', transform_bold_to_t1w, 'reference_image')
    wf.connect(reverse_transforms, 'reverse_list', transform_bold_to_t1w, 'transforms')

    transform_ref_bold = pe.MapNode(ants.ApplyTransforms(dimension=3, 
                                                         float=True, 
                                                         interpolation='LanczosWindowedSinc'),
                                    iterfield=['input_image', 'transforms'],
                               name='transform_ref_bold')

    wf.connect(remove_hmc,  'out_list', transform_ref_bold, 'transforms')
    wf.connect(inputnode, 'ref_bold', transform_ref_bold, 'input_image')
    wf.connect(gen_ref, 'out_file', transform_ref_bold, 'reference_image')

    get_TR = pe.MapNode(niu.Function(function=_get_TR,
                                     input_names=['bold_metadata'],
                                     output_names=['tr']),
                        iterfield=['bold_metadata'],
                        name='get_TR')
    
    wf.connect(inputnode, 'bold_metadata', get_TR, 'bold_metadata')

    merge = pe.MapNode(fsl.Merge(dimension='t'), iterfield=['in_files', 'tr'], name='merge')
    wf.connect(transform_bold_to_t1w, 'out_files', merge, 'in_files')
    wf.connect(get_TR, 'tr', merge, 'tr')

    ds_bold_t1w = pe.MapNode(DerivativesDataSink(out_path_base='spynoza',
                                                    suffix='preproc',
                                                    base_directory=derivatives_dir),
                                iterfield=['in_file', 'source_file'],
                                name='ds_bold_t1w')

    wf.connect(inputnode, 'bold', ds_bold_t1w, 'source_file')


    if highpass:
        filter_node = pe.MapNode(niu.Function(function=savgol_filter,
                                              input_names=['in_file',
                                                           'polyorder',
                                                           'deriv',
                                                           'window_length',
                                                           'tr'],
                                              output_names=['out_file']),
                                 iterfield=['in_file', 'tr'],
                                 name='filter_node')

        wf.connect(merge, 'merged_file', filter_node, 'in_file')
        wf.connect(get_TR, 'tr', filter_node, 'tr')
        filter_node.inputs.polyorder = 3
        filter_node.inputs.deriv = 0
        filter_node.inputs.window_length = 128

        psc_convert = pe.MapNode(niu.Function(function=percent_signal_change,
                                              input_names=['in_file'],
                                              output_names=['out_file']),
                                 iterfield=['in_file'],
                                 name='psc_convert')

        wf.connect(filter_node, 'out_file', psc_convert, 'in_file')
        wf.connect(psc_convert, 'out_file', ds_bold_t1w, 'in_file') 

    else:
        wf.connect(merge, 'merged_file', ds_bold_t1w, 'in_file')

    ds_ref_mask_t1w = pe.MapNode(DerivativesDataSink(out_path_base='spynoza',
                                                    suffix='mask',
                                                    base_directory=derivatives_dir),
                                iterfield=['in_file'],
                                name='ds_ref_mask_t1w')

    wf.connect(inputnode, ('bold', pickfirst), ds_ref_mask_t1w, 'source_file')
    wf.connect(transform_ref_mask2, 'output_image', ds_ref_mask_t1w, 'in_file')

    ds_ref_bold_t1w = pe.MapNode(DerivativesDataSink(out_path_base='spynoza',
                                                    suffix='reference',
                                                    base_directory=derivatives_dir),
                                iterfield=['in_file', 'source_file'],
                                name='ds_ref_bold_t1w')

    wf.connect(inputnode, 'bold', ds_ref_bold_t1w, 'source_file')
    wf.connect(transform_ref_bold, 'output_image', ds_ref_bold_t1w, 'in_file')

    outputnode = pe.Node(niu.IdentityInterface(fields=['bold_in_T1w',
                                                       'ref_mask_in_T1w']),
                         name='outputnode')

    wf.connect(ds_bold_t1w, 'out_file', outputnode, 'bold_in_t1w')

    return wf


def _make_list_from_element(element, template_list):
    return [element] * len(template_list)


def argmax(in_values):
    import numpy as np
    return np.argmax(in_values)

def argmin(in_values):
    import numpy as np
    return np.argmin(in_values)

def reverse(in_values):
    return in_values[::-1]

def get_last(in_list, n=3):
    return in_list[-n:]

def pick_from(in_list, n=2):
    return in_list[n:]

def pick_until(in_list, n=-1):
    return in_list[:n]

def invert_mask(mask_file):
    from nilearn import image
    import os
    from nipype.utils.filemanip import split_filename

    d, fn, ext = split_filename(mask_file)

    mask = image.math_img('(mask -1) * -1', mask=mask_file)
    new_fn = os.path.abspath(fn + '_inv' + ext)

    mask.to_filename(new_fn)

    return new_fn
def _get_TR(bold_metadata):
    return bold_metadata['RepetitionTime']
