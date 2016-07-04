def topup_scan_params(pe_direction='y', te=0.025, epi_factor=37):

    import numpy as np

    scan_param_array = np.zeros((2, 4))
    scan_param_array[0, ['x', 'y', 'z'].index(pe_direction)] = 1
    scan_param_array[1, ['x', 'y', 'z'].index(pe_direction)] = -1
    scan_param_array[:, -1] = te * epi_factor

    return scan_param_array

def apply_scan_params(pe_direction='y', te=0.025, epi_factor=37, nr_trs=1):

    import numpy as np

    scan_param_array = np.zeros((nr_trs, 4))
    scan_param_array[:, ['x', 'y', 'z'].index(pe_direction)] = 1
    scan_param_array[:, -1] = te * epi_factor



