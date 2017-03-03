import nipype.pipeline as pe
import os.path as op
from nipype.interfaces.utility import Function, IdentityInterface
from .nodes import Melodic4fix
from ..utils import extract_task


def create_melodic_workflow(name='melodic', template=None, varnorm=True):

    input_node = pe.Node(IdentityInterface(
        fields=['in_file']), name='inputspec')

    output_node = pe.Node(IdentityInterface(
        fields=['out_dir']), name='outputspec')

    if template is None:
        template = op.join(op.dirname(op.dirname(op.abspath(__file__))),
                           'data', 'fsf_templates', 'melodic_template.fsf')

    melodic4fix_node = pe.MapNode(interface=Melodic4fix,
                                  iterfield=['in_file', 'out_dir'],
                                  name='melodic4fix')

    # Don't know if this works. Could also set these defaults inside the
    # melodic4fix node definition...
    melodic4fix_node.inputs.template = template
    melodic4fix_node.inputs.varnorm = varnorm

    rename_ica = pe.MapNode(Function(input_names=['in_file'],
                                     output_names=['out_file'],
                                     function=extract_task),
                            name='rename_ica', iterfield=['in_file'])

    mel4fix_workflow = pe.Workflow(name=name)

    mel4fix_workflow.connect(input_node, 'in_file',
                             melodic4fix_node, 'in_file')

    mel4fix_workflow.connect(input_node, 'in_file',
                             rename_ica, 'in_file')

    mel4fix_workflow.connect(rename_ica, 'out_file',
                             melodic4fix_node, 'out_dir')

    mel4fix_workflow.connect(melodic4fix_node, 'out_dir',
                             output_node, 'out_dir')

    return mel4fix_workflow


def create_fix_workflow(name='fsl_fix'):
    print('Not yet implemented!')
    pass


def create_ica_fix_denoising_workflow(name='ica_fix_denoising'):
    print("Not yet implemented")
    pass



