def _extract_task(in_file):
    import os.path as op

    task_name = in_file.split('task-')[-1].split('_')[0]
    return op.abspath(task_name)


# FUNCTION
def melodic4fix(in_file, out_dir, template, varnorm=True):

    import os
    import numpy as np
    import subprocess
    import nibabel as nib
    import os.path as op

    varnorm = "1" if varnorm else "0"

    with open(template, 'rb') as f:
        template = f.readlines()

    template = [txt.replace('\n', '') for txt in template if txt != '\n']
    template = [txt for txt in template if txt[0] != '#']  # remove comments

    hdr = nib.load(in_file).header

    # IMPORTANT: might need TE value???

    arg_dict = {'tr': hdr['pixdim'][4],
                'npts': hdr['dim'][4],
                'feat_files': "\"%s\"" % in_file,
                'outputdir': "\"%s\"" % out_dir,
                'varnorm': varnorm,
                'totalVoxels': np.prod(hdr['dim'][1:5])}

    fsf_out = []

    # Loop over lines in cleaned template-fsf
    for line in template:

        if any(key in line for key in arg_dict.keys()):
            parts = [txt for txt in line.split(' ') if txt]
            keys = [key for key in arg_dict.keys() if key in line][0]
            values = arg_dict[keys]

            parts[-1] = values
            parts = [str(p) for p in parts]
            fsf_out.append(" ".join(parts))
        else:
            fsf_out.append(line)

    with open(op.join(out_dir, 'melodic.fsf'), 'wb') as outfile:
        outfile.write("\n".join(fsf_out))

    cmd = ['feat', outfile]
    with open(os.devnull, 'w') as devnull:
        subprocess.call(cmd, stdout=devnull)

    return out_dir


def create_melodic_workflow(name='melodic', template=None, varnorm=True):

    import nipype.pipeline as pe
    import os.path as op
    from nipype.interfaces.utility import Function, IdentityInterface

    if template is None:
        template = op.abspath(op.join('fsf_templates', 'melodic_template.fsf'))

    input_node = pe.Node(IdentityInterface(
        fields=['in_file']), name='inputspec')

    output_node = pe.Node(IdentityInterface(
        fields=['out_dir']), name='outputspec')

    melodic4fix_node = pe.MapNode(Function(input_names=['in_file', 'out_dir',
                                                        'template',
                                                        'varnorm'],
                                           output_names=['out_dir'],
                                           function=melodic4fix),
                                  name='melodic4fix',
                                  iterfield=['in_file', 'out_dir'])

    rename_ica = pe.MapNode(Function(input_names=['in_file'],
                                     output_names=['out_file'],
                                     function=_extract_task),
                            name='rename_ica', iterfield=['in_file'])

    melodic_workflow = pe.Workflow(name=name)
    melodic_workflow.connect(input_node, 'in_file', melodic4fix_node, 'in_file')
    melodic_workflow.connect(input_node, 'in_file', rename_ica, 'in_file')
    melodic_workflow.connect(rename_ica, 'out_file', melodic4fix_node, 'out_dir')
    melodic_workflow.connect(melodic4fix_node, 'out_dir', output_node, 'out_dir')

    return melodic_workflow


def create_fix_workflow(name='fsl_fix'):
    pass


