import nipype.pipeline as pe
from nipype.interfaces.utility import IdentityInterface
from nipype.interfaces.io import DataSink
from ..nodes import Concat_confound_files
from nipype.algorithms.confounds import FramewiseDisplacement

from .nodes import Extend_motion_parameters


def create_motion_confound_workflow(order=2, fd_cutoff=.2,
                                    name='motion_confound'):

    input_node = pe.Node(interface=IdentityInterface(fields=[
        'par_file',
        'output_directory',
        'sub_id'
    ]), name='inputspec')

    output_node = pe.Node(interface=IdentityInterface(fields=[
        'out_fd',
        'out_ext_moco'
    ]), name='outputspec')

    datasink = pe.Node(DataSink(), name='sinker')
    datasink.inputs.parameterization = False

    extend_motion_parameters = pe.MapNode(Extend_motion_parameters,
                                          iterfield=['par_file'],
                                          name='extend_motion_parameters')
    extend_motion_parameters.inputs.order = order

    framewise_disp = pe.MapNode(FramewiseDisplacement(parameter_source='FSL'),
                                iterfield=['in_file'], name='framewise_disp')

    mcf_wf = pe.Workflow(name=name)
    mcf_wf.connect(input_node, 'output_directory', datasink, 'base_directory')
    mcf_wf.connect(input_node, 'sub_id', datasink, 'container')
    mcf_wf.connect(input_node, 'par_file', extend_motion_parameters, 'par_file')
    mcf_wf.connect(input_node, 'par_file', framewise_disp, 'in_file')
    mcf_wf.connect(extend_motion_parameters, 'out_ext',
                   output_node, 'out_ext_moco')
    mcf_wf.connect(framewise_disp, 'out_file', output_node, 'out_fd')
    mcf_wf.connect(extend_motion_parameters, 'out_ext',
                   datasink, 'confounds')
    mcf_wf.connect(framewise_disp, 'out_file', datasink, 'confounds.@df')

    return mcf_wf