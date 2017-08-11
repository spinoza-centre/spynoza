from nipype.interfaces.utility import Function


def topup_scan_params(pe_direction='y', te=0.025, epi_factor=37):
    import numpy as np
    import os
    import tempfile

    scan_param_array = np.zeros((2, 4))
    scan_param_array[0, ['x', 'y', 'z'].index(pe_direction)] = 1
    scan_param_array[1, ['x', 'y', 'z'].index(pe_direction)] = -1
    scan_param_array[:, -1] = te * epi_factor

    spa_txt = str('\n'.join(
        ['\t'.join(['%1.3f' % s for s in sp]) for sp in scan_param_array]))

    fn = os.path.join(tempfile.gettempdir(), 'scan_params.txt')
    np.savetxt(fn, scan_param_array, fmt=str('%1.3f'))
    return fn


Topup_scan_params = Function(function=topup_scan_params,
                             input_names=['pe_direction', 'te', 'epi_factor'],
                             output_names=['fn'])


def apply_scan_params(pe_direction='y', te=0.025, epi_factor=37, nr_trs=1):
    import numpy as np
    import os
    import tempfile

    scan_param_array = np.zeros((nr_trs, 4))
    scan_param_array[:, ['x', 'y', 'z'].index(pe_direction)] = 1
    scan_param_array[:, -1] = te * epi_factor

    spa_txt = str('\n'.join(
        ['\t'.join(['%1.3f' % s for s in sp]) for sp in scan_param_array]))

    fn = os.path.join(tempfile.gettempdir(), 'scan_params_apply.txt')
    np.savetxt(fn, scan_param_array, fmt='%1.3f')
    return fn


Apply_scan_params = Function(function=apply_scan_params,
                             input_names=['pe_direction', 'te', 'epi_factor',
                                          'nr_trs'],
                             output_names=['fn'])
