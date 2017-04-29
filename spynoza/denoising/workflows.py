# master workflow
import nipype.pipeline as pe
from nipype.interfaces.utility import IdentityInterface
from nipype.algorithms.confounds import ComputeDVARS
from nipype.interfaces.io import DataSink
from .compcor import create_compcor_workflow
from .motion_confounds import create_motion_confound_workflow
from .nodes import Concat_confound_files

def create_confound_workflow(name='confound'):

    input_node = pe.Node(interface=IdentityInterface(fields=[
        'in_file',
        'par_file',
        'fast_files',
        'highres2epi_mat',
        'n_comp_tcompcor',
        'n_comp_acompcor',
        'output_directory',
        'sub_id'
    ]), name='inputspec')

    output_node = pe.Node(interface=IdentityInterface(fields=[
        'all_confounds',
    ]), name='outputspec')

    datasink = pe.Node(DataSink(), name='sinker')
    datasink.inputs.parameterization = False

    compute_DVARS = pe.MapNode(ComputeDVARS(save_all=True, remove_zerovariance=True),
                               iterfield=['in_file', 'in_mask'], name='compute_DVARS')

    motion_wf = create_motion_confound_workflow(order=2)

    confound_wf = pe.Workflow(name=name)
    confound_wf.connect(input_node, 'par_file',
                        motion_wf, 'inputspec.par_file')
    confound_wf.connect(input_node, 'sub_id',
                        motion_wf, 'inputspec.sub_id')
    confound_wf.connect(input_node, 'output_directory',
                        motion_wf, 'inputspec.output_directory')

    compcor_wf = create_compcor_workflow()
    confound_wf.connect(input_node, 'in_file',
                        compcor_wf, 'inputspec.in_file')
    confound_wf.connect(input_node, 'fast_files',
                        compcor_wf, 'inputspec.fast_files')
    confound_wf.connect(input_node, 'highres2epi_mat',
                        compcor_wf, 'inputspec.highres2epi_mat')
    confound_wf.connect(input_node, 'n_comp_tcompcor',
                        compcor_wf, 'inputspec.n_comp_tcompcor')
    confound_wf.connect(input_node, 'n_comp_acompcor',
                        compcor_wf, 'inputspec.n_comp_acompcor')
    confound_wf.connect(input_node, 'sub_id',
                        compcor_wf, 'inputspec.sub_id')
    confound_wf.connect(input_node, 'output_directory',
                        compcor_wf, 'inputspec.output_directory')

    confound_wf.connect(compcor_wf, 'outputspec.epi_mask', compute_DVARS,
                        'in_mask')
    confound_wf.connect(input_node, 'in_file', compute_DVARS, 'in_file')

    concat = pe.MapNode(Concat_confound_files, iterfield=['ext_par_file',
                                                          'fd_file',
                                                          'dvars_file'],
                        name='concat')

    confound_wf.connect(motion_wf, 'outputspec.out_ext_moco', concat, 'ext_par_file')
    confound_wf.connect(motion_wf, 'outputspec.out_fd', concat, 'fd_file')
    confound_wf.connect(compcor_wf, 'outputspec.acompcor_file', concat,
                        'acompcor_file')
    #confound_wf.connect(compcor_wf, 'outputspec.tcompcor_file', concat,
    #                    'tcompcor_file')
    confound_wf.connect(compute_DVARS, 'out_all', concat, 'dvars_file')
    confound_wf.connect(input_node, 'sub_id', datasink, 'sub_id')
    confound_wf.connect(input_node, 'output_directory', datasink, 'base_directory')
    confound_wf.connect(concat, 'out_file', datasink, 'confounds')

    return confound_wf