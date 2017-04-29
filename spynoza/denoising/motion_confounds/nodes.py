from nipype.interfaces.utility import Function


def extend_motion_parameters(par_file, order=2):
    """ Extends the motion parameters """
    import numpy as np
    import os.path as op
    import pandas as pd
    from copy import copy

    moco_pars = np.loadtxt(par_file)
    col_names = ['X', 'Y', 'Z', 'Rot_X', 'Rot_Y', 'Rot_Z']
    df_orig = pd.DataFrame(moco_pars, columns=col_names)
    fn_orig = op.abspath('original_motion_pars.tsv')
    df_orig.to_csv(fn_orig, sep=str('\t'), index=False)

    current_names = copy(col_names)
    current_pars = copy(moco_pars)
    suffix = 'dt'

    for i in range(order):
        tmp_d = np.diff(np.vstack((np.ones((1, 6)), current_pars)), axis=0)
        tmp_amp = tmp_d ** 2
        current_pars = tmp_d
        moco_pars = np.hstack((moco_pars, tmp_d, tmp_amp))
        current_names.extend([s + '_%s' % suffix for s in col_names])
        current_names.extend([s + '_%s_sq' % suffix for s in col_names])
        suffix = 'd' + suffix

    df_ext = pd.DataFrame(moco_pars, columns=current_names)
    fn_ext = op.abspath('extended_motion_pars.tsv')
    df_ext.to_csv(fn_ext, sep=str('\t'), index=False)
    return fn_ext


Extend_motion_parameters = Function(function=extend_motion_parameters,
                                    input_names=['par_file', 'order'],
                                    output_names=['out_ext'])
