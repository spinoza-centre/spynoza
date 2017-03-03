# Implementation of savitsky-golay filter in a format compatible
# with a Nipype node.

from __future__ import division, print_function, absolute_import
from nipype.interfaces.utility import Function


def savgol_filter(in_file, polyorder=3, deriv=0, window_length=120, tr=None):
    """ Applies a savitsky-golay filter to a nifti-file.

    Fits a savitsky-golay filter to a 4D fMRI nifti-file and subtracts the
    fitted data from the original data to effectively remove low-frequency
    signals.

    Parameters
    ----------
    in_file : str
        Absolute path to nifti-file.
    polyorder : int (default: 3)
        Order of polynomials to use in filter.
    deriv : int (default: 0)
        Number of derivatives to use in filter.
    window_length : int (default: 120)
        Window length in seconds.

    Returns
    -------
    out_file : str
        Absolute path to filtered nifti-file.
    """

    import nibabel as nib
    from scipy.signal import savgol_filter
    import numpy as np
    import os

    data = nib.load(in_file)
    dims = data.shape
    affine = data.affine
    header = data.header

    if tr is None:  # if TR is not set
        tr = data.header['pixdim'][4]

    # TR must be in seconds
    if tr < 0.01:
        tr = np.round(tr * 1000, decimals=3)
    if tr > 20:
        tr = tr / 1000.0

    window = np.int(window_length / tr)

    # Window must be odd
    if window % 2 == 0:
        window += 1

    data = data.get_data().reshape((np.prod(data.shape[:-1]), data.shape[-1]))
    data_filt = savgol_filter(data, window_length=window, polyorder=polyorder,
                              deriv=deriv, axis=1, mode='nearest')

    data_filt = data - data_filt + data_filt.mean(axis=-1)[:, np.newaxis]
    data_filt = data_filt.reshape(dims)
    img = nib.Nifti1Image(data_filt, affine=affine, header=header)
    new_name = os.path.basename(in_file).split('.')[:-2][0] + '_sg.nii.gz'
    out_file = os.path.abspath(new_name)
    nib.save(img, out_file)
    return out_file


Savgol_filter = Function(function=savgol_filter,
                         input_names=['in_file', 'polyorder', 'deriv',
                                      'window_length', 'tr'],
                         output_names=['out_file'])