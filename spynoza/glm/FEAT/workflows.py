from nipype.interfaces.utility import IdentityInterface
import nipype.pipeline as pe
from nipype.interfaces.utility import Rename
from nipype.interfaces.fsl.model import Level1Design, FEAT
from ..workflows import create_modelgen_workflow
from .nodes import Rename_feat_dir
from ...utils import Extract_task


def create_firstlevel_workflow_FEAT(name='level1feat'):

    input_node = pe.Node(IdentityInterface(fields=['events_file',
                                                   'single_trial',
                                                   'sort_by_onset',
                                                   'exclude',
                                                   'func_file',
                                                   'TR',
                                                   'confound_file',
                                                   'which_confounds',
                                                   'extend_motion_pars',
                                                   'model_serial_correlations',
                                                   'hrf_base',
                                                   'hp_filter',
                                                   'contrasts'
                                                   ]), name='inputspec')

    output_node = pe.Node(IdentityInterface(fields=['fsf_file', 'ev_file', 'feat_dir']),
                          name='outputspec')

    level1_design = pe.MapNode(interface=Level1Design(bases={'dgamma': {'derivs': True}},
                                                      interscan_interval=2.0,
                                                      model_serial_correlations=True),
                               iterfield=['contrasts', 'session_info'], name='level1_design')

    feat = pe.MapNode(interface=FEAT(), iterfield=['fsf_file'], name='FEAT')
    extract_task = pe.MapNode(interface=Extract_task, iterfield=['in_file'], name='extract_task')
    rename_feat_dir = pe.MapNode(interface=Rename_feat_dir,
                                 iterfield=['feat_dir', 'task'],
                                 name='rename_feat_dir')

    firstlevel_wf = pe.Workflow(name=name)

    modelgen_wf = create_modelgen_workflow()

    firstlevel_wf.connect(input_node, 'events_file', modelgen_wf, 'inputspec.events_file')
    firstlevel_wf.connect(input_node, 'func_file', modelgen_wf, 'inputspec.func_file')
    firstlevel_wf.connect(input_node, 'TR', modelgen_wf, 'inputspec.TR')
    firstlevel_wf.connect(input_node, 'single_trial', modelgen_wf, 'inputspec.single_trial')
    firstlevel_wf.connect(input_node, 'sort_by_onset', modelgen_wf, 'inputspec.sort_by_onset')
    firstlevel_wf.connect(input_node, 'extend_motion_pars', modelgen_wf, 'inputspec.extend_motion_pars')
    firstlevel_wf.connect(input_node, 'exclude', modelgen_wf, 'inputspec.exclude')
    firstlevel_wf.connect(input_node, 'confound_file', modelgen_wf, 'inputspec.confound_file')
    firstlevel_wf.connect(input_node, 'which_confounds', modelgen_wf, 'inputspec.which_confounds')                                               
    firstlevel_wf.connect(input_node, 'hp_filter', modelgen_wf, 'inputspec.hp_filter')                                               

    firstlevel_wf.connect(input_node, 'TR', level1_design, 'interscan_interval')
    firstlevel_wf.connect(input_node, 'model_serial_correlations', level1_design, 'model_serial_correlations')
    firstlevel_wf.connect(input_node, 'hrf_base', level1_design, 'bases')
    firstlevel_wf.connect(input_node, 'contrasts', level1_design, 'contrasts')

    firstlevel_wf.connect(modelgen_wf, 'outputspec.session_info', level1_design, 'session_info')
    firstlevel_wf.connect(level1_design, 'fsf_files', feat, 'fsf_file')
    firstlevel_wf.connect(level1_design, 'fsf_files', output_node, 'fsf_file')
    firstlevel_wf.connect(level1_design, 'ev_files', output_node, 'ev_file')

    firstlevel_wf.connect(input_node, 'func_file', extract_task, 'in_file')
    firstlevel_wf.connect(extract_task, 'task_name', rename_feat_dir, 'task')
    firstlevel_wf.connect(feat, 'feat_dir', rename_feat_dir, 'feat_dir')
    firstlevel_wf.connect(rename_feat_dir, 'feat_dir', output_node, 'feat_dir')

    return firstlevel_wf
