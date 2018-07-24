import os.path as op
from nipype.interfaces.utility import Function


def FS_aseg_file_create(freesurfer_subject_ID, freesurfer_subject_dir, aseg):
    return op.join(freesurfer_subject_dir, freesurfer_subject_ID, 'mri', aseg)

FS_aseg_file = Function(input_names=('freesurfer_subject_ID', 'freesurfer_subject_dir'),
                        output_names='aseg_mgz_path',
                        function=FS_aseg_file_create)


def FS_label_list_glob(freesurfer_subject_ID, freesurfer_subject_dir,
                  label_directory, re='*.label'):
    import glob
    import os.path as op

    label_list = glob.glob(
        op.join(freesurfer_subject_dir, freesurfer_subject_ID, 'label',
                label_directory, re))

    return label_list


FS_LabelNode = Function(input_names=('freesurfer_subject_ID',
                                           'freesurfer_subject_dir',
                                           'label_directory', 're'),
                              output_names='label_list',
                              function=FS_label_list_glob)
