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


def concat_iterables(sub, sess=None):
    """ Concatenates subject and session iterables.

    Generates a subject/session output-directory for datasink.inputs.container.

    Inputs
    ------
    sub : str
        Subject-id (e.g. sub-001)
    sess : str
        Session-id (e.g. sess-001)

    Returns
    -------
    out_name : str
        Concatenation of iterables (if sess is defined)
    """
    import os

    if sess is None:
        out_name = sub
    else:
        out_name = os.path.join(sub, sess)

    return out_name


def topup_scan_params(pe_direction='y', te=0.025, epi_factor=37):

    import numpy as np
    import os
    import tempfile

    scan_param_array = np.zeros((2, 4))
    scan_param_array[0, ['x', 'y', 'z'].index(pe_direction)] = 1
    scan_param_array[1, ['x', 'y', 'z'].index(pe_direction)] = -1
    scan_param_array[:, -1] = te * epi_factor

    spa_txt = str('\n'.join(['\t'.join(['%1.3f'%s for s in sp]) for sp in scan_param_array]))

    fn = os.path.join(tempfile.gettempdir(), 'scan_params.txt')
    # with open(fn, 'wt', encoding='utf-8') as f:
    #     f.write(spa_txt)

    np.savetxt(fn, scan_param_array, fmt='%1.3f')
    return fn

def apply_scan_params(pe_direction='y', te=0.025, epi_factor=37, nr_trs=1):

    import numpy as np
    import os
    import tempfile

    scan_param_array = np.zeros((nr_trs, 4))
    scan_param_array[:, ['x', 'y', 'z'].index(pe_direction)] = 1
    scan_param_array[:, -1] = te * epi_factor

    spa_txt = str('\n'.join(['\t'.join(['%1.3f'%s for s in sp]) for sp in scan_param_array]))

    fn = os.path.join(tempfile.gettempdir(), 'scan_params_apply.txt')
    # with open(fn, 'wt', encoding='utf-8') as f:
    #     f.write(spa_txt)

    np.savetxt(fn, scan_param_array, fmt='%1.3f')
    return fn

def pickfirst(files):
    if isinstance(files, list):
        if len(files) > 0:
            return files[0]
        else:
            return files
    else:
        return files

def percent_signal_change(in_file, func = 'mean'):
    """Converts data in a nifti-file to percent signal change.

    Takes a 4D fMRI nifti-file and subtracts the
    mean data from the original data, after which division 
    by the mean or median and multiplication with 100.

    Parameters
    ----------
    in_file : str
        Absolute path to nifti-file.
    func : string ['mean', 'median'] (default: 'mean')
        the function used to calculate the first moment

    Returns
    -------
    out_file : str
        Absolute path to converted nifti-file.
    """

    import nibabel as nib
    import numpy as np
    import os

    data = nib.load(in_file)
    dims = data.shape
    affine = data.affine

    if func == 'mean':
        data_m = data.get_data().mean(axis = -1)
    elif func == 'median':
        data_m = np.median(data.get_data(), axis = -1)
    data_psc = 100.0 * (data.get_data() - data_m) / data_m
    img = nib.Nifti1Image(data_filt, affine)

    new_name = os.path.basename(in_file).split('.')[:-2][0] + '_psc.nii.gz'
    out_file = os.path.abspath(new_name)
    nib.save(img, out_file)

    return out_file