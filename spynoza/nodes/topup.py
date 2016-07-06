def topup_scan_params(pe_direction='y', te=0.025, epi_factor=37):

    import numpy as np
    import os

    scan_param_array = np.zeros((2, 4))
    scan_param_array[0, ['x', 'y', 'z'].index(pe_direction)] = 1
    scan_param_array[1, ['x', 'y', 'z'].index(pe_direction)] = -1
    scan_param_array[:, -1] = te * epi_factor

    fn = os.path.abspath('scan_params.txt')
    np.savetxt(fn, scan_param_array, fmt='%1.3f')
    return fn

def apply_scan_params(pe_direction='y', te=0.025, epi_factor=37, nr_trs=1):

    import numpy as np
    import os

    scan_param_array = np.zeros((nr_trs, 4))
    scan_param_array[:, ['x', 'y', 'z'].index(pe_direction)] = 1
    scan_param_array[:, -1] = te * epi_factor

    fn = os.path.abspath('scan_params_apply.txt')
    np.savetxt(fn, scan_param_array, fmt='%1.3f')
    return fn


