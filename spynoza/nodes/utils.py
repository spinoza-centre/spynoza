from __future__ import division, print_function


def EPI_file_selector(which_file, in_files):
    """Selects which EPI file will be the standard EPI space.
    Choices are: 'middle', 'last', 'first', or any integer in the list
    """
    import math

    if which_file == 'middle':
        return in_files[int(math.floor(len(in_files)/2))]
    elif which_file == 'first':
        return in_files[0]
    elif which_file == 'last':
        return in_files[-1]
    elif type(which_file) == int:
        return in_files[which_file]


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
    import bottleneck as bn

    data = nib.load(in_file)
    dims = data.shape
    affine = data.affine

    if func == 'mean':
        data_m = bn.nanmean(data.get_data(), axis=-1)
    elif func == 'median':
        data_m = np.nanmedian(data.get_data(), axis=-1)

    data_psc = (100.0 * (data.get_data().transpose((3,0,1,2)) - data_m) / data_m).transpose((1,2,3,0))
    img = nib.Nifti1Image(data_psc, affine)

    new_name = os.path.basename(in_file).split('.')[:-2][0] + '_psc.nii.gz'
    out_file = os.path.abspath(new_name)
    nib.save(img, out_file)

    return out_file

def average_over_runs(in_files, func = 'mean'):
    """Converts data in a nifti-file to percent signal change.

    Takes a list of 4D fMRI nifti-files and averages them. 
    That is, the resulting file has the same dimensions as each
    of the input files. average_over_runs assumes that all nifti
    files to be averaged have identical dimensions.

    Parameters
    ----------
    in_files : list
        Absolute paths to nifti-files.
    func : string ['mean', 'median'] (default: 'mean')
        the function used to calculate the 'average'

    Returns
    -------
    out_file : str
        Absolute path to average nifti-file.
    """

    import nibabel as nib
    import numpy as np
    import os

    template_data = nib.load(in_files[0])
    dims = template_data.shape
    affine = template_data.affine
    all_data = np.zeros([len(in_files)]+list(dims))
    
    for i in range(len(in_files)):
        d = nib.load(in_files[i])
        all_data[i] = d.get_data()

    if func == 'mean':
        av_data = all_data.mean(axis = 0)
    elif func == 'median':
        av_data = np.median(all_data, axis = 0)

    img = nib.Nifti1Image(av_data, affine)

    new_name = os.path.basename(in_files[0]).split('.')[:-2][0] + '_av.nii.gz'
    out_file = os.path.abspath(new_name)
    nib.save(img, out_file)

    return out_file

def pickle_to_json(in_file):
    import json
    import jsonpickle
    import pickle
    import os.path as op

    with open(in_file, 'rU') as f:
        jsp = jsonpickle.encode(pickle.load(f))

    out_file = op.abspath(op.splitext(in_file)[0] + '.json')
    with open(out_file, 'w') as f:
        json.dump(jsp, f, indent = 2)

    return out_file






