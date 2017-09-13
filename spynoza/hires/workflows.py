import nipype.pipeline.engine as pe
import nipype.interfaces.utility as niu
from nipype.interfaces import fsl, ants, afni
from nipype.interfaces.base import isdefined
import pkg_resources

from ..utils import EPI_file_selector, average_over_runs, get_scaninfo, init_temporally_crop_run_wf, pickfirst

from ..motion_correction.workflows import create_motion_correction_workflow
from ..unwarping.topup.workflows import create_bids_topup_workflow
from ..registration.sub_workflows import create_epi_to_T1_workflow

from spynoza.io.bids import collect_data

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
                            t1w_mask=None,
                            crop_bold_epis=True,
                            topup_package='afni',
                            polish=True):
    
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
         * T1w_epi:        Use a T1-weighted image with similar distortions as the 
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
    polish : bool
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
    t1w_epi : list/filename
        T1-weighted EPI with same distortions as bold_epi.
        
    """
    
    wf = pe.Workflow(name=name)
    
    fields = ['bold_epi', 'T1w']
    
    if method == 'topup':
        fields += ['epi_op',
                   'bold_epi_metadata',
                   'epi_op_metadata']
    elif method == 'T1w_epi':
        fields += ['T1w_epi']
    
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
        if method == 'T1w_epi':
            inputspec.inputs.t1w_epi = t1w_epi
        else:
            raise Exception('t1w_epi can only be set when using T1w_EPI method')

    if t1w:
        inputspec.inputs.T1w = t1w

            
    
    #  *** TOPUP ***
    if method == 'topup':
        
        # *** only ONE warpfield ***
        if single_warpfield:

            if polish:
                raise Exception('When using a single warpfield for \
                                all BOLD runs, there is little use for polishing, right?')
            
            mc_wf_bold_epi = create_motion_correction_workflow(name='mc_wf_bold_epi',
                                                               output_mask=True,
                                                               method='FSL',
                                                               lightweight=True)
            
            mc_wf_bold_epi.inputs.inputspec.which_file_is_EPI_space = register_to
            
            
            wf.connect(inputspec, 'bold_epi', mc_wf_bold_epi, 'inputspec.in_files')
                
            
            mc_wf_epi_op = create_motion_correction_workflow(name='mc_wf_epi_op',
                                                             method='FSL',
                                                             output_mask=True,
                                                             lightweight=True)
            
            mc_wf_epi_op.inputs.inputspec.which_file_is_EPI_space = register_to
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

            registration_wf = create_epi_to_T1_workflow(package='ants',
                                                        parameter_file=linear_registration_parameters,
                                                        init_reg_file=init_reg_file)

            wf.connect(topup_wf, 'outputspec.bold_epi_corrected', registration_wf, 'inputspec.EPI_space_file')
            wf.connect(inputspec, 'T1w', registration_wf, 'inputspec.T1_file')
            
            merge_bold_epi_to_T1w = pe.Node(niu.Merge(2), name='merge_bold_epi_to_T1w')
            wf.connect(registration_wf, 'outputspec.EPI_T1_matrix_file', merge_bold_epi_to_T1w, 'in1')
            wf.connect(topup_wf, 'outputspec.bold_epi_unwarp_field', merge_bold_epi_to_T1w, 'in2')

            transform_epi_to_T1w = pe.MapNode(ants.ApplyTransforms(dimension=3,
                                                                float=True,
                                                                interpolation='LanczosWindowedSinc'),
                                              iterfield=['input_image'],
                                              name='transform_epi_to_T1w')

            wf.connect(applymask_bold_epi, 'out_file', transform_epi_to_T1w, 'input_image')
            wf.connect(inputspec, 'T1w', transform_epi_to_T1w, 'reference_image')
            wf.connect(merge_bold_epi_to_T1w, 'out', transform_epi_to_T1w, 'transforms')

            out_fields = ['bold_epi_mc', 'bold_epi_mask', 'bold_epi_to_T1w_transforms', 'T1w_to_bold_epi_transforms', 'mean_epi_in_T1w_space']
            outputspec = pe.Node(niu.IdentityInterface(fields=out_fields),
                                 name='outputspec')

            make_list_of_transforms = pe.Node(niu.Function(function=_make_list_from_element),
                                              name='make_list_of_transforms')

            wf.connect(mc_wf_bold_epi, 'outputspec.motion_corrected_files', outputspec, 'bold_epi_mc')
            wf.connect(mc_wf_bold_epi, 'outputspec.EPI_space_mask', outputspec, 'bold_epi_mask')
            wf.connect(merge_bold_epi_to_T1w, 'out', make_list_of_transforms, 'element')
            wf.connect(mc_wf_bold_epi, 'outputspec.motion_corrected_files', make_list_of_transforms, 'template_list')

            wf.connect(make_list_of_transforms, 'out', outputspec, 'bold_epi_to_T1w_transforms')
            wf.connect(transform_epi_to_T1w, 'output_image', outputspec, 'mean_epi_in_T1w_space')

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
                    

                mc_wf_epi_op = create_motion_correction_workflow(name='mc_wf_epi_ops',
                                                                 method='FSL',
                                                                 output_mask=True,
                                                                 lightweight=True)
                
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
            
            
                applymask_bold_epi = pe.Node(fsl.ApplyMask(),
                                                name="applymask_bold_epi")
                run_wf.connect(mean_bold_epi1, 'out_file', applymask_bold_epi, 'in_file') 
                run_wf.connect(mc_wf_bold_epi, 'outputspec.EPI_space_mask', applymask_bold_epi, 'mask_file') 

                applymask_epi_op = pe.Node(fsl.ApplyMask(), name="applymask_epi_op")
                run_wf.connect(mc_wf_epi_op, 'outputspec.EPI_space_file', applymask_epi_op, 'in_file') 
                run_wf.connect(mc_wf_epi_op, 'outputspec.EPI_space_mask', applymask_epi_op, 'mask_file') 


                topup_wf = create_bids_topup_workflow(package=topup_package)

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
                    registration_wf = create_epi_to_T1_workflow(package='ants',
                                                                parameter_file=linear_registration_parameters,
                                                                init_reg_file=init_reg_file[ix])
                else:
                    registration_wf = create_epi_to_T1_workflow(package='ants',
                                                                parameter_file=linear_registration_parameters,
                                                                init_reg_file=init_reg_file)

                run_wf.connect(topup_wf, 'outputspec.bold_epi_corrected', registration_wf, 'inputspec.EPI_space_file')
                wf.connect(inputspec, 'T1w', run_wf, 'epi_to_T1.inputspec.T1_file')

                wf.connect(run_wf, 'bids_topup_workflow.outputspec.bold_epi_unwarp_field', \
                           merge_topup_corrections_runs, 'in%s' % ix)

                wf.connect(run_wf, 'epi_to_T1.outputspec.EPI_T1_matrix_file', \
                           merge_epi_to_T1w_transforms_runs, 'in%s' % ix)

                wf.connect(run_wf, 'applymask_bold_epi.out_file', \
                           merge_mean_epis, 'in%s' % ix)

                wf.connect(run_wf, 'mc_wf_bold_epi.outputspec.motion_corrected_files', \
                           merge_mc_epis, 'in%s' % ix)

                wf.connect(run_wf, 'mc_wf_bold_epi.outputspec.EPI_space_mask', \
                           merge_epi_masks, 'in%s' % ix)


            merge_bold_epi_to_T1w = pe.MapNode(niu.Merge(2),
                                               iterfield=['in1', 'in2'],
                                               name='merge_bold_epi_to_T1w')
            transform_epi_to_T1w_no_polish = pe.MapNode(ants.ApplyTransforms(dimension=3,
                                                                float=True,
                                                                interpolation='LanczosWindowedSinc'),
                                              iterfield=['input_image',
                                                         'transforms'],
                                              name='transform_epi_to_T1w_no_polish')
            
            wf.connect(merge_epi_to_T1w_transforms_runs, 'out', merge_bold_epi_to_T1w, 'in1')
            wf.connect(merge_topup_corrections_runs, 'out', merge_bold_epi_to_T1w, 'in2')

            transform_epi_to_T1w = pe.MapNode(ants.ApplyTransforms(dimension=3,
                                                                float=True,
                                                                interpolation='LanczosWindowedSinc'),
                                              iterfield=['input_image', 'transforms'],
                                              name='transform_epi_to_T1w')

            wf.connect(merge_mean_epis, 'out', transform_epi_to_T1w, 'input_image')
            wf.connect(inputspec, 'T1w', transform_epi_to_T1w, 'reference_image')
            wf.connect(merge_bold_epi_to_T1w, 'out', transform_epi_to_T1w, 'transforms')

            out_fields = ['bold_epi_mc',
                          'bold_epi_mask',
                          'bold_epi_to_T1w_transforms',
                          'mean_epi_in_T1w_space']

            outputspec = pe.Node(niu.IdentityInterface(fields=out_fields),
                                 name='outputspec')

            wf.connect(merge_mc_epis, 'out', outputspec, 'bold_epi_mc')
            wf.connect(merge_epi_masks, 'out', outputspec, 'bold_epi_mask')

            if polish:
                polish_wf = create_polish_EPI_registrations_wf()

                wf.connect(inputspec, 'T1w', polish_wf, 'inputspec.T1w')
                wf.connect(transform_epi_to_T1w, 'output_image', polish_wf, 'inputspec.EPI_runs')


                add_polish_transforms = pe.MapNode(niu.Merge(2),
                                                   iterfield=['in1', 'in2'],
                                                   name='add_polish_transforms')

                wf.connect(polish_wf, 'outputspec.transforms', add_polish_transforms, 'in1')
                wf.connect(merge_bold_epi_to_T1w, 'out', add_polish_transforms, 'in2')

                polished_transformer = pe.MapNode(ants.ApplyTransforms(dimension=3,
                                                                float=True,
                                                                interpolation='LanczosWindowedSinc'),
                                              iterfield=['input_image', 'transforms'],
                                              name='polished_transformer')

                wf.connect(merge_mean_epis, 'out', polished_transformer, 'input_image')
                wf.connect(inputspec, 'T1w', polished_transformer, 'reference_image')
                wf.connect(add_polish_transforms, 'out', polished_transformer, 'transforms')

                wf.connect(add_polish_transforms, 'out', outputspec, 'bold_epi_to_T1w_transforms')
                wf.connect(polished_transformer, 'output_image', outputspec, 'mean_epi_in_T1w_space')

            else:
                wf.connect(merge_bold_epi_to_T1w, 'out', outputspec, 'bold_epi_to_T1w_transforms')
                wf.connect(transform_epi_to_T1w, 'output_image', outputspec, 'mean_epi_in_T1w_space')



            
    return wf

def create_polish_EPI_registrations_wf(method='best-run',
                                       apply_transform=False,
                                       linear_registration_parameters='linear_hires.json'):
    """ Given a set of EPI runs registered to a
    T1w-image. Register the EPI runs to each other, to maximize overlap"""
    import numpy as np

    if method != 'best-run':
        raise NotImplementedError('Nope.')

    fields = ['EPI_runs', 'T1w']

    inputspec = pe.Node(niu.IdentityInterface(fields=fields),
                        name='inputspec')

    wf = pe.Workflow(name='polish_registration')

    mean_epis = pe.Node(niu.Function(function=average_over_runs),
                         name='mean_epis')

    epi_masker = pe.Node(afni.Automask(outputtype='NIFTI_GZ'),
                        name='epi_masker')

    measure_similarity = pe.MapNode(ants.MeasureImageSimilarity(metric='MI',
                                                                dimension=3,
                                                                metric_weight=1.0,
                                                                radius_or_number_of_bins=5,
                                                                sampling_strategy='Regular',
                                                                sampling_percentage=1.0),
                                    iterfield=['moving_image'],
                                    name='measure_similarity')

    wf.connect(inputspec, 'EPI_runs', mean_epis, 'in_files')
    wf.connect(mean_epis, 'out', epi_masker, 'in_file')

    wf.connect(epi_masker, 'out_file', measure_similarity, 'fixed_image_mask')


    wf.connect(inputspec, 'T1w', measure_similarity, 'fixed_image')
    wf.connect(inputspec, 'EPI_runs', measure_similarity, 'moving_image')

    bold_registration_json = pkg_resources.resource_filename('spynoza.data.ants_json', linear_registration_parameters)
    ants_registration = pe.MapNode(ants.Registration(from_file=bold_registration_json,
                                                  output_warped_image=apply_transform), 
                                   iterfield=['moving_image'],
                                name='ants_registration')
    
    select_reference_epi = pe.Node(niu.Select(),
                                   name='select_reference_epi')

    wf.connect(inputspec, 'EPI_runs', select_reference_epi, 'inlist')
    wf.connect(measure_similarity, ('similarity', argmax), select_reference_epi, 'index')

    wf.connect(select_reference_epi, ('out', pickfirst), ants_registration, 'fixed_image')

    wf.connect(epi_masker, 'out_file', ants_registration, 'fixed_image_masks')
    wf.connect(inputspec, 'EPI_runs', ants_registration, 'moving_image')

    out_fields = ['transforms', 'transformed_epis']

    outputspec = pe.Node(niu.IdentityInterface(fields=out_fields),
                         name='outputspec')

    wf.connect(ants_registration, 'warped_image', outputspec, 'transformed_epis')
    wf.connect(ants_registration, 'forward_transforms', outputspec, 'transforms')

    return wf



def _make_list_from_element(element, template_list):
    return [element] * len(template_list)


def argmax(in_values):
    import numpy as np
    return np.argmax(in_values)
