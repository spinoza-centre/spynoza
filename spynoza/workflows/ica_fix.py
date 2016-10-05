from nipype.interfaces.fsl.model import MELODIC


def _rename_outdir(in_file):
    import os.path as op

    task_name = in_file.split('task-')[-1].split('_')[0]
    return op.join(op.dirname(in_file), task_name)


def create_ica_workflow(name='ica_fix'):

    import nipype.pipeline as pe
    from nipype.interfaces.utility import Function, IdentityInterface

    input_node = pe.Node(IdentityInterface(
        fields=['in_file', 'fix_classifier']), name='inputspec')

    output_node = pe.Node(IdentityInterface(
        fields=['out_dir']), name='outputspec')

    rename_ica = pe.MapNode(Function(input_names=['in_file'],
                                     output_names=['out_file'],
                                     function=_rename_outdir),
                            name='rename_ica', iterfield=['in_file'])

    melodic = pe.MapNode(interface=MELODIC(report=False, out_all=True,
                                           approach='symm'),
                         name='melodic', iterfield=['in_files', 'out_dir'])

    ica_workflow = pe.Workflow(name=name)
    ica_workflow.connect(input_node, 'in_file', melodic, 'in_files')
    ica_workflow.connect(input_node, 'in_file', rename_ica, 'in_file')
    ica_workflow.connect(rename_ica, 'out_file', melodic, 'out_dir')
    ica_workflow.connect(melodic, 'out_dir', output_node, 'out_dir')

    return ica_workflow