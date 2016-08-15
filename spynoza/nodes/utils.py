from __future__ import division, print_function


def get_scaninfo(in_file):
    """ Extracts info from nifti file.

    Extracts affine, shape (x, y, z, t), dynamics (t), voxel-size and TR from
    a given nifti-file.

    Parameters
    ----------
    in_file : nifti-file (*.nii.gz or *.nii)
        Nifti file to extract info from.

    Returns
    -------
    TR : float
        Temporal resolution of functional scan
    shape : tuple
        Dimensions of scan (x, y, z, time)
    dyns : int
        Number of dynamics (time)
    voxsize : tuple
        Size of voxels (x, y, z = slice thickness)
    affine : np.ndarray
        Affine matrix.
    """
    import nibabel as nib

    nifti = nib.load(in_file)
    affine = nifti.affine
    shape = nifti.shape
    dyns = nifti.shape[-1]
    voxsize = nifti.header['pixdim'][1:4]
    TR = float(nifti.header['pixdim'][4])

    return TR, shape, dyns, voxsize, affine


def dyns_min_1(dyns):
    dyns_1 = dyns - 1
    return dyns_1

def topup_scan_params(pe_direction='y', te=0.025, epi_factor=37):

    import numpy as np
    import os
    import tempfile

    scan_param_array = np.zeros((2, 4))
    scan_param_array[0, ['x', 'y', 'z'].index(pe_direction)] = 1
    scan_param_array[1, ['x', 'y', 'z'].index(pe_direction)] = -1
    scan_param_array[:, -1] = te * epi_factor

    fn = os.path.join(tempfile.gettempdir(), 'scan_params.txt')
    np.savetxt(fn, scan_param_array, fmt='%1.3f')
    return fn

def apply_scan_params(pe_direction='y', te=0.025, epi_factor=37, nr_trs=1):

    import numpy as np
    import os
    import tempfile

    scan_param_array = np.zeros((nr_trs, 4))
    scan_param_array[:, ['x', 'y', 'z'].index(pe_direction)] = 1
    scan_param_array[:, -1] = te * epi_factor

    fn = os.path.join(tempfile.gettempdir(), 'scan_params_apply.txt')
    np.savetxt(fn, scan_param_array, fmt='%1.3f')
    return fn