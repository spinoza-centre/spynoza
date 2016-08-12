import os.path as op
import nipype.pipeline as pe

def find_config_file(conf_file):
    if conf_file == '':
        conf_file = op.join(op.abspath(__file__), 'sub_workflows', 'b02b0.cnf')

    return conf_file

def topup_workflow_wrapper(raw_file, alt_file, alt_t, conf_file, pe_direction, te, epi_factor):
    """Wraps the function that creates the topup workflow for MapNode behavior"""
    from sub_workflows.topup import create_topup_workflow

    tu_wf = create_topup_workflow()
    tu_wf.inputspec.raw_file = raw_file
    tu_wf.inputspec.alt_file = alt_file
    tu_wf.inputspec.alt_t = alt_t
    tu_wf.inputspec.conf_file = conf_file
    tu_wf.inputspec.pe_direction = pe_direction
    tu_wf.inputspec.te = te
    tu_wf.inputspec.epi_factor = epi_factor

    return tu_wf


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
    >>> topup_all_workflow.inputs.inputspec.raw_files = ['sub-001.nii.gz','sub-002.nii.gz']
    >>> topup_all_workflow.inputs.inputspec.alt_files = ['sub-001_topup.nii.gz','sub-002_topup.nii.gz']
    >>> topup_all_workflow.inputs.inputspec.conf_file = '' # empty string defaults to included file
    >>> topup_all_workflow.inputs.inputspec.output_directory = '/data/project/raw/BIDS/sj_1/'
 
    Inputs::
          inputspec.output_directory : directory in which to sink the result files
          inputspec.raw_files : list of functional files to be topup-unwarped.
          inputspec.alt_files : the opposite pe direction files. 
          inputspec.conf_file : file to configure topup with. 
    Outputs::
           outputspec.corrected_files : list of corrected files
    """

    ### NODES
    input_node = pe.Node(IdentityInterface(fields=['raw_files', 'alt_files', 'output_directory', 'conf_file']), name='inputspec')
    output_node = pe.Node(IdentityInterface(fields=([
    			'corrected_files' ])), name='outputspec')

    find_config_node = pe.Node(Function(input_names='config_file', output_names='config_file',
                                function=find_config_file), name='find_config_file')

    ########################################################################################
    # Topup for a single run is already a workflow, and we want to mapnode over this,
    # preferentially. The only way to do this is wrap the workflow in a function, 
    # and make a mapnode of this function. 
    ########################################################################################

    topup_workflow_wrapper_node = pe.MapNode(Function(input_names=
        ['in_file', 'alt_file', 'alt_t', 'conf_file', 'pe_direction', 'te', 'epi_factor'], 
        output_names='topup_workflow',
        function=topup_workflow_wrapper), name='topup_workflow_wrapper_node', iterfield=['in_file', 'alt_file'])

    topup_workflow_wrapper_node.inputs.alt_t = session_info['alt_t']
    topup_workflow_wrapper_node.inputs.te = session_info['te']
    topup_workflow_wrapper_node.inputs.pe_direction = session_info['pe_direction']
    topup_workflow_wrapper_node.inputs.epi_factor = session_info['epi_factor']

    ########################################################################################
    # And the actual across-runs workflow.
    ########################################################################################    

    topup_all_workflow = pe.Workflow(name='topup_all_workflow')
    topup_all_workflow.connect(input_node, 'conf_file', find_config_node, 'conf_file')
    topup_all_workflow.connect(find_config_node, 'conf_file', topup_workflow_wrapper_node, 'conf_file')
    topup_all_workflow.connect(input_node, 'raw_files', topup_workflow_wrapper_node, 'in_file')
    topup_all_workflow.connect(input_node, 'alt_files', topup_workflow_wrapper_node, 'alt_file')


    ########################################################################################
    # and the output node. 
    ########################################################################################    
    topup_all_workflow.connect(topup_workflow_wrapper_node, 'out_file', output_node, 'corrected_files')

    ########################################################################################
    # outputs via datasink
    ########################################################################################
    datasink = pe.Node(nio.DataSink(), name='sinker')

    # first link the workflow's output_directory into the datasink.
    motion_correction_workflow.connect(input_node, 'output_directory', datasink, 'base_directory')
    # and the rest
    motion_correction_workflow.connect(topup_workflow_wrapper_node, 'out_file', datasink, 'tu')

    return topup_all_workflow
