from nipype.interfaces.utility import Function


def rename_feat_dir(feat_dir, task):
    """ Renames the FEAT directory from fsl.FEAT.

    Mimicks nipype.utility.Rename, but Rename doesn't
    work for directories (it seems ...), and this function
    *does*.

    Parameters
    ----------
    feat_dir : str
        Path to feat-directory (output from fsl.FEAT node)
    task : str
        Name of task to give to the feat-directory (e.g. workingmemory,
        such that the name becomes workingmemory.feat)
    """

    import os.path as op
    import shutil

    new_name = op.basename(feat_dir).replace('run0.feat', '%s.feat' % task)
    dst = op.abspath(new_name)
    shutil.copytree(feat_dir, dst)
    
    return dst


Rename_feat_dir = Function(function=rename_feat_dir, input_names=['feat_dir', 'task'],
                           output_names=['feat_dir'])