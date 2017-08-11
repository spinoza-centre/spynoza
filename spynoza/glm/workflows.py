from nipype.interfaces.utility import IdentityInterface
import nipype.pipeline as pe
from nipype.algorithms.modelgen import SpecifyModel
from .nodes import Events_file_to_bunch, Combine_events_and_confounds, Load_confounds


def create_modelgen_workflow(name='modelgen', skip_specify_model=False):
    input_node = pe.Node(IdentityInterface(fields=['events_file',
                                                   'single_trial',
                                                   'sort_by_onset',
                                                   'exclude',
                                                   'func_file',
                                                   'TR',
                                                   'confound_file',
                                                   'which_confounds',
                                                   'extend_motion_pars',
                                                   'hp_filter',
                                                   ]), name='inputspec')

    output_node = pe.Node(IdentityInterface(fields=['session_info']),
                          name='outputspec')

    events_file_to_bunch = pe.MapNode(Events_file_to_bunch,
                                      iterfield=['in_file'],
                                      name='events_file_to_bunch')

    load_confounds = pe.MapNode(Load_confounds,
                                iterfield=['in_file'], name='load_confounds')

    combine_evs = pe.MapNode(Combine_events_and_confounds,
                             iterfield=['subject_info', 'confound_names', 'confounds'],
                             name='combine_evs')

    
    modelgen_wf = pe.Workflow(name=name)
    modelgen_wf.connect(input_node, 'events_file', events_file_to_bunch, 'in_file')
    modelgen_wf.connect(input_node, 'single_trial', events_file_to_bunch, 'single_trial')
    modelgen_wf.connect(input_node, 'sort_by_onset', events_file_to_bunch, 'sort_by_onset')
    modelgen_wf.connect(input_node, 'exclude', events_file_to_bunch, 'exclude')
    
    modelgen_wf.connect(input_node, 'confound_file', load_confounds, 'in_file')
    modelgen_wf.connect(input_node, 'which_confounds', load_confounds, 'which_confounds')
    modelgen_wf.connect(input_node, 'extend_motion_pars', load_confounds, 'extend_motion_pars')
    modelgen_wf.connect(events_file_to_bunch, 'subject_info', combine_evs, 'subject_info')
    modelgen_wf.connect(load_confounds, 'regressor_names', combine_evs, 'confound_names')
    modelgen_wf.connect(load_confounds, 'regressors', combine_evs, 'confounds')
    
    if skip_specify_model:
        modelgen_wf.connect(combine_evs, 'subject_info', output_node, 'session_info')
    else:
        specify_model = pe.MapNode(SpecifyModel(input_units='secs'),
                               iterfield=['subject_info', 'functional_runs'],
                               name='specify_model')
        modelgen_wf.connect(input_node, 'hp_filter', specify_model, 'high_pass_filter_cutoff')
        modelgen_wf.connect(combine_evs, 'subject_info', specify_model, 'subject_info')
        modelgen_wf.connect(input_node, 'func_file', specify_model, 'functional_runs')
        modelgen_wf.connect(input_node, 'TR', specify_model, 'time_repetition')
        modelgen_wf.connect(specify_model, 'session_info', output_node, 'session_info')

    return modelgen_wf
