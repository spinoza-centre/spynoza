from __future__ import division, print_function

def convert_edf_2_hdf5(edf_file, low_pass_pupil_f = 6.0, high_pass_pupil_f = 0.01):
    """converts the edf_file to hdf5 using hedfpy
    
    Requires hedfpy

    Parameters
    ----------
    edf_file : str
        absolute path to edf file.
    low_pass_pupil_f : float
        low pass cutoff frequency for band-pass filtering of the pupil signal
    high_pass_pupil_f : float
        high pass cutoff frequency for band-pass filtering of the pupil signal
    Returns
    -------
    hdf5_file : str
        absolute path to hdf5 file.
    """

    import os.path as op
    from hedfpy.HDFEyeOperator import HDFEyeOperator

    hdf5_file = op.abspath(op.splitext(edf_file)[0] + '.h5')
    alias = op.splitext(op.split(edf_file)[-1])[0]

    ho = HDFEyeOperator(hdf5_file)
    ho.add_edf_file(edf_file)
    ho.edf_message_data_to_hdf(alias = alias)
    ho.edf_gaze_data_to_hdf(alias = alias, pupil_hp = high_pass_pupil_f, pupil_lp = low_pass_pupil_f)

    return hdf5_file

