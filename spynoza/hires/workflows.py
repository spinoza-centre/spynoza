import nipype.pipeline.engine as pe
import nipype.interfaces.utility as niu
from nipype.interfaces import fsl, ants

from ..utils import EPI_file_selector, average_over_runs, get_scaninfo, init_temporally_crop_run_wf
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

            
    
    #  *** TOPUP ***
    if method == 'topup':
        
        # *** only ONE warpfield ***
        if single_warpfield:
            
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
            wf.connect(mean_epi_op2, 'out', topup_wf, 'inputspec.epi_op')
            wf.connect(inputspec, 'bold_epi_metadata', topup_wf, 'inputspec.bold_epi_metadata')
            wf.connect(inputspec, 'epi_op_metadata', topup_wf, 'inputspec.epi_op_metadata')

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

            
    return wf


def _make_list_from_element(element, template_list):
    return [element] * len(template_list)


