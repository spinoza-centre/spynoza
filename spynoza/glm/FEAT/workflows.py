from nipype.interfaces.utility import IdentityInterface
import nipype.pipeline as pe
from nipype.interfaces.io import DataSink
from nipype.interfaces.fsl.model import Level1Design, FEAT
from ..workflows import create_modelgen_workflow


def create_firstlevel_workflow(name='level1'):

    input_node = pe.Node(IdentityInterface(fields=['events_file',
                                                   'func_file',
                                                   'TR',
                                                   'realignment_parameters',
                                                   'model_serial_correlations',
                                                   'contrasts',
                                                   'output_directory',
                                                   'sub_id']), name='inputspec')

    output_node = pe.Node(IdentityInterface(fields=['fsf_file', 'ev_file', 'feat_dir']),
                          name='outputspec')

    datasink = pe.Node(interface=DataSink(), name='datasink')
    datasink.inputs.parameterization = False

    level1_design = pe.MapNode(interface=Level1Design(bases={'dgamma': {'derivs': True}},
                                                      interscan_interval=2.0,
                                                      model_serial_correlations=True),
                               iterfield=['contrasts', 'session_info'], name='level1_design')

    feat = pe.MapNode(interface=FEAT(), iterfield=['fsf_file'], name='FEAT')

    firstlevel_wf = pe.Workflow(name=name)
    modelgen_wf = create_modelgen_workflow()
    firstlevel_wf.connect(input_node, 'events_file', modelgen_wf, 'inputspec.events_file')
    firstlevel_wf.connect(input_node, 'func_file', modelgen_wf, 'inputspec.func_file')
    firstlevel_wf.connect(input_node, 'TR', modelgen_wf, 'inputspec.TR')
    firstlevel_wf.connect(input_node, 'realignment_parameters', modelgen_wf, 'inputspec.realignment_parameters')
    firstlevel_wf.connect(input_node, 'TR', level1_design, 'interscan_interval')
    firstlevel_wf.connect(input_node, 'model_serial_correlations', level1_design, 'model_serial_correlations')
    firstlevel_wf.connect(input_node, 'contrasts', level1_design, 'contrasts')
    firstlevel_wf.connect(input_node, 'output_directory', datasink, 'base_directory')
    firstlevel_wf.connect(input_node, 'sub_id', datasink, 'container')

    firstlevel_wf.connect(modelgen_wf, 'outputspec.session_info', level1_design, 'session_info')
    firstlevel_wf.connect(level1_design, 'fsf_files', feat, 'fsf_file')
    firstlevel_wf.connect(level1_design, 'fsf_files', output_node, 'fsf_file')
    firstlevel_wf.connect(level1_design, 'ev_files', output_node, 'ev_file')

    firstlevel_wf.connect(feat, 'feat_dir', output_node, 'feat_dir')
    firstlevel_wf.connect(feat, 'feat_dir', datasink, 'firstlevel')

    return firstlevel_wf