import os.path as op
import json
import nipype.pipeline as pe
from sub_workflows import *

def create_topup_all_workflow(name = 'topup_all', session_info ):
	"""uses sub-workflows to perform different registration steps.
    Requires fsl and freesurfer tools
    Parameters
    ----------
    name : string
        name of workflow
    session_info : dict 
        contains session information needed for workflow, such as
        which file to moco to, etc.
    
    Example
    -------
    >>> topup_all_workflow = create_topup_all_workflow('topup_all_workflow', session_info = {'use_FS':True})
    >>> topup_all_workflow.inputs.inputspec.raw_files = '/data/project/raw/BIDS/sj_1/'
    >>> topup_all_workflow.inputs.inputspec.raw_topup_files = ['sub-001.nii.gz','sub-002.nii.gz']
    >>> topup_all_workflow.inputs.inputspec.output_directory = 'middle'
    >>> topup_all_workflow.inputs.inputspec.output_directory = 'middle'
 
    Inputs::
          inputspec.output_directory : directory in which to sink the result files
          inputspec.in_files : list of functional files
          inputspec.which_file_is_EPI_space : determines which file is the 'standard EPI space'
    Outputs::
           outputspec.EPI_space_file : standard EPI space file, one timepoint
           outputspec.motion_corrected_files : motion corrected files
           outputspec.motion_correction_plots : motion correction plots
           outputspec.motion_correction_parameters : motion correction parameters
    """

    ### NODES
    input_node = pe.Node(IdentityInterface(fields=['raw_files', 'raw_topup_files', 'output_directory']), name='inputspec')
    output_node = pe.Node(IdentityInterface(fields=([
    			'corrected_files', ])), name='outputspec')

    topup_all_workflow = pe.Workflow(name='topup_all_workflow')

    topup = pe.MapNode(interface=create_topup_workflow(),
                       name='topup', iterfield='in_file')


    base_dir = '/media/lukas/data/Spynoza_data/data_tomas/sub-001'
    raw_nii = op.join(base_dir, 'func', 'sub-001_task-mapper_acq-multiband_run-1_bold.nii.gz')
    topup_raw_nii = op.join(base_dir, 'fmap', 'sub-001_task-mapper_acq-multiband_run-1_topup.nii.gz')
    config_file = op.join(op.dirname(base_dir), 'b02b0.cnf')

    topup_workflow = create_topup_workflow()
    topup_workflow.inputs.inputnode.in_file = raw_nii
    topup_workflow.inputs.inputnode.alt_file = topup_raw_nii
    topup_workflow.inputs.inputnode.alt_t = 0
    topup_workflow.inputs.inputnode.conf_file = config_file
    topup_workflow.inputs.inputnode.pe_direction = 'y'
    topup_workflow.inputs.inputnode.te = 0.025
    topup_workflow.inputs.inputnode.epi_factor = 37