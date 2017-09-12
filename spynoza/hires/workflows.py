import nipype.pipeline.engine as pe
import nipype.interfaces.utility as niu
from nipype.interfaces import fsl

from ..utils import EPI_file_selector, average_over_runs
from ..motion_correction.workflows import create_motion_correction_workflow
from ..utils import get_scaninfo, init_temporally_crop_run_wf


def init_hires_unwarping_wf(name="unwarp_hires",
                            method='topup',
                            single_warpfield=False,
                            register_to='last',
                            linear_registration_parameters='linear_hires',
                            nonlinear_registration_parameters='nonlinear_precise',
                            bold_epi=None,
                            epi_op=None,
                            t1w_epi=None,
                            crop_bold_epis=True,
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
    
    fields = ['bold_epi']
    
    if method == 'topup':
        fields += ['epi_op']
    elif method == 'T1w_epi':
        fields += ['T1w_epi']
    
    inputspec = pe.Node(niu.IdentityInterface(fields=fields),
                        name='inputspec')
    
    if bold_epi:
        inputspec.inputs.bold_epi = bold_epi
        
    if epi_op:
        if method == 'topup':
            inputspec.inputs.epi_op = epi_op
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
                                                               method='FSL',
                                                               lightweight=True)
            
            mc_wf_bold_epi.inputs.inputspec.which_file_is_EPI_space = register_to
            
            if crop_bold_epis:
                crop_bold_epi_wf = init_temporally_crop_run_wf()
                wf.connect(inputspec, 'bold_epi', crop_bold_epi_wf, 'inputspec.in_files')
                wf.connect(inputspec, 'epi_op', crop_bold_epi_wf, 'inputspec.templates')
                wf.connect(crop_bold_epi_wf, 'outputspec.out_files', mc_wf_bold_epi, 'inputspec.in_files')
            else:
                wf.connect(inputspec, 'bold_epi', mc_wf_bold_epi, 'inputspec.in_files')
            
            mc_wf_epi_op = create_motion_correction_workflow(name='mc_wf_epi_op',
                                                               method='FSL',
                                                               lightweight=True)
            
            mc_wf_epi_op.inputs.inputspec.which_file_is_EPI_space = register_to
            wf.connect(inputspec, 'epi_op', mc_wf_epi_op, 'inputspec.in_files')
            
            mean_bold_epis1 = pe.MapNode(fsl.MeanImage(dimension='T'), 
                                         iterfield=['in_file'],
                                         name='mean_bold_epis')
            mean_epis_op1 = pe.MapNode(fsl.MeanImage(dimension='T'), 
                                       iterfield=['in_file'],
                                       name='mean_epis_op')
            
            wf.connect(mc_wf_bold_epi, 'outputspec.motion_corrected_files', mean_bold_epis1, 'in_file')
            wf.connect(mc_wf_epi_op, 'outputspec.motion_corrected_files', mean_epis_op1, 'in_file')
            
#             mean_bold_epis2 = pe.Node(niu.Function(function=average_over_runs),
#                                      name='mean_bold_epis2')
#             mean_epi_op2 = pe.Node(niu.Function(function=average_over_runs),
#                                      name='mean_epi_op2')
            
#             wf.connect(mean_bold_epis1, 'out_file', mean_bold_epis2, 'in_files')
#             wf.connect(mean_epis_op1, 'out_file', mean_epi_op2, 'in_files')            
            
            
    return wf



