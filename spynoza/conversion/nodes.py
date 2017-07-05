# Implementation of savitsky-golay filter in a format compatible
# with a Nipype node.

from __future__ import division, print_function, absolute_import
import nipype.pipeline as pe
from nipype.interfaces.utility import Function

def percent_signal_change(in_file, func='mean'):
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
    header = data.header

    if func == 'mean':
        data_m = bn.nanmean(data.get_data(), axis=-1)
    elif func == 'median':
        data_m = bn.nanmedian(data.get_data(), axis=-1)

    data_psc = (100.0 * (np.nan_to_num(data.get_data()).transpose(
        (3, 0, 1, 2)) - data_m) / data_m).transpose((1, 2, 3, 0))
    img = nib.Nifti1Image(np.nan_to_num(data_psc), affine=affine, header=header)

    new_name = os.path.basename(in_file).split('.')[:-2][0] + '_psc.nii.gz'
    out_file = os.path.abspath(new_name)
    nib.save(img, out_file)

    return out_file


# function for percent signal change
Percent_signal_change = Function(function=percent_signal_change,
                                 input_names=['in_file', 'func'],
                                 output_names=['out_file'])

# node for percent signal change
psc = pe.MapNode(Function(input_names=['in_file', 'func'],
                                output_names=['out_file'],
                                function=percent_signal_change),
                                name='percent_signal_change',
                                iterfield=['in_file'])