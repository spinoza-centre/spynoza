from nipype.interfaces.utility import Function


def confound_to_outlier(in_file, threshold, col_name=None, **kwargs):
    """ Converts a confound array to outliers, given a threshold.

    Parameters
    ----------
    in_file : str
        Path to csv/tsv file that can be imported using pandas.
    threshold : float
        Threshold to apply to confound.
    col_name : str
        Specific column-name to apply threshold to.
    """

    pass


def concat_confound_files(ext_par_file, fd_file, dvars_file, acompcor_file):
    """ Concatenates confound files. """
    import pandas as pd
    import os.path as op

    confound_tsvs = [ext_par_file, fd_file, acompcor_file, dvars_file]

    df = pd.concat([pd.read_csv(f, sep=str('\t')) for f in confound_tsvs], axis=1)
    fn = op.abspath('all_confounds.tsv')
    df.to_csv(fn, sep=str('\t'), index=None)

    return fn


Concat_confound_files = Function(function=concat_confound_files,
                                 input_names=['ext_par_file',
                                              'fd_file',
                                              'dvars_file',
                                              'acompcor_file'],
                                 output_names=['out_file'])

