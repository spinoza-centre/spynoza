from nipype.interfaces.utility import Function


def melodic4fix(in_file, out_dir, template, varnorm):

    import os
    import numpy as np
    import subprocess
    import nibabel as nib
    import os.path as op

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
                'varnorm': "1" if varnorm else "0",
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


Melodic4fix = Function(function=melodic4fix,
                       input_names=['in_file', 'out_dir', 'template',
                                    'varnorm'],
                       output_names=['out_dir'])
