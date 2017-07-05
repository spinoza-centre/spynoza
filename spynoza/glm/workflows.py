from nipype.interfaces.utility import IdentityInterface
import nipype.pipeline as pe
from nipype.algorithms.modelgen import SpecifyModel
from .nodes import Events_file_to_bunch


def create_modelgen_workflow(name='modelgen'):
    input_node = pe.Node(IdentityInterface(fields=['events_file',
                                                   'func_file',
                                                   'TR',
                                                   'realignment_parameters',
                                                   'output_directory',
                                                   'sub_id']), name='inputspec')

    output_node = pe.Node(IdentityInterface(fields=['session_info']),
                          name='outputspec')

    events_file_to_bunch = pe.MapNode(Events_file_to_bunch,
                                      iterfield=['in_file'],
                                      name='events_file_to_bunch')

    specify_model = pe.MapNode(SpecifyModel(input_units='secs',
                                            parameter_source='FSL',
                                            high_pass_filter_cutoff=100),
                               iterfield=['subject_info', 'functional_runs',
                                          'realignment_parameters'],
                               name='specify_model')

    modelgen_wf = pe.Workflow(name=name)
    modelgen_wf.connect(input_node, 'events_file', events_file_to_bunch, 'in_file')
    modelgen_wf.connect(input_node, 'func_file', specify_model, 'functional_runs')
    modelgen_wf.connect(input_node, 'TR', specify_model, 'time_repetition')
    modelgen_wf.connect(input_node, 'realignment_parameters', specify_model, 'realignment_parameters')

    modelgen_wf.connect(events_file_to_bunch, 'bunch', specify_model, 'subject_info')
    modelgen_wf.connect(specify_model, 'session_info', output_node, 'session_info')

    return modelgen_wf
