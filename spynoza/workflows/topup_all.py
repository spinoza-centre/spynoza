import os.path as op
import nipype.pipeline as pe
from .sub_workflows import *
from nipype.interfaces.utility import Function, IdentityInterface

# def find_config_file(conf_file):
#     import os.path as op
#     if conf_file == '':
#         out_file = '/usr/share/fsl/5.0/etc/flirtsch/b02b0.cnf'
#     else:
#         out_file = conf_file
#     return out_file

# def topup_workflow_wrapper(in_file, alt_file, alt_t, conf_file, pe_direction, te, epi_factor):
#     """Wraps the function that creates the topup workflow for MapNode behavior"""
#     from spynoza.workflows.sub_workflows.topup import create_topup_workflow

#     tu_wf = create_topup_workflow()
#     tu_wf.inputs.inputspec.in_file = in_file
#     tu_wf.inputs.inputspec.alt_file = alt_file
#     tu_wf.inputs.inputspec.alt_t = alt_t
#     tu_wf.inputs.inputspec.conf_file = conf_file
#     tu_wf.inputs.inputspec.pe_direction = pe_direction
#     tu_wf.inputs.inputspec.te = te
#     tu_wf.inputs.inputspec.epi_factor = epi_factor


#     ########################################################################################
#     # if we don't call 'run' by hand here, the node that surrounds this function 
#     # will only return the workflow object when its 'run' is called, which doesn't actually
#     # run the workflow in question. this is a horrible hack of course. 
#     ########################################################################################
    
#     tu_wf.run()
#     return tu_wf


def create_topup_all_workflow(session_info, name = 'topup_all' ):
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

    # import os.path as op
    # import nipype.pipeline as pe
    # import nipype.interfaces.io as nio
    # from nipype.interfaces.utility import Function, IdentityInterface
    # from spynoza.workflows.sub_workflows.topup import create_topup_workflow

    ### NODES
    input_node = pe.Node(IdentityInterface(fields=['in_files', 'alt_files', 'output_directory', 'conf_file']), name='inputspec')
    output_node = pe.Node(IdentityInterface(fields=([
    			'corrected_files' ])), name='outputspec')

    # find_config_node = pe.Node(Function(input_names='conf_file', output_names='out_file',
    #                             function=find_config_file), name='find_config_node')

    join_node = pe.JoinNode(IdentityInterface(fields=['topup_outputs']), # 
            joinsource = 'topup_workflow_wrapper_node', 
            joinfield = 'topup_outputs', 
            name = 'joiner')
    ########################################################################################
    # Topup for a single run is already a workflow, and we want to mapnode over this,
    # preferentially. The only way to do this is wrap the workflow in a function, 
    # and make a mapnode of this function. 
    ########################################################################################

    topup_workflow_wrapper_node = pe.MapNode(Function(output_names='outputspec.out_file', input_names='name',
        function=create_topup_workflow), name='topup_workflow_wrapper_node', iterfield=['inputspec.in_file', 'inputspec.alt_file'])

    topup_workflow_wrapper_node.inputs.inputspec.alt_t = session_info['alt_t']
    topup_workflow_wrapper_node.inputs.inputspec.te = session_info['te']
    topup_workflow_wrapper_node.inputs.inputspec.pe_direction = session_info['pe_direction']
    topup_workflow_wrapper_node.inputs.inputspec.epi_factor = session_info['epi_factor']

    ########################################################################################
    # And the actual across-runs workflow.
    ########################################################################################    

    topup_all_workflow = pe.Workflow(name='topup_all_workflow')
    # topup_all_workflow.connect(input_node, 'conf_file', find_config_node, 'conf_file')
    # topup_all_workflow.connect(find_config_node, 'out_file', topup_workflow_wrapper_node, 'inputspec.conf_file')
    topup_all_workflow.connect(input_node, 'conf_file', topup_workflow_wrapper_node, 'inputspec.conf_file')
    topup_all_workflow.connect(input_node, 'in_files', topup_workflow_wrapper_node, 'inputspec.in_file')
    topup_all_workflow.connect(input_node, 'alt_files', topup_workflow_wrapper_node, 'inputspec.alt_file')

    ########################################################################################
    # and the output. 
    ########################################################################################    
    topup_all_workflow.connect(topup_workflow_wrapper_node, 'outputspec.out_file', output_node, 'corrected_files')
    # topup_all_workflow.connect(topup_workflow_wrapper_node, 'outputspec.out_file', join_node, 'topup_outputs')
    # topup_all_workflow.connect(join_node, 'topup_outputs', output_node, 'corrected_files')


    ########################################################################################
    # outputs via datasink
    ########################################################################################
    datasink = pe.Node(nio.DataSink(infields=['topup'], container = ''), name='sinker')

    # first link the workflow's output_directory into the datasink.
    topup_all_workflow.connect(input_node, 'output_directory', datasink, 'base_directory')
    # and the rest
    # topup_all_workflow.connect(join_node, 'topup_outputs', datasink, 'topup')
    topup_all_workflow.connect(topup_workflow_wrapper_node, 'outputspec.out_file', datasink, 'topup')

    return topup_all_workflow
