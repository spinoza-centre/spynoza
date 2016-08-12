import os.path as op
import glob
import nipype.pipeline as pe
from nipype.interfaces import fsl
from nipype.interfaces import freesurfer
from nipype.interfaces.utility import IdentityInterface


def create_masks_from_surface_workflow(name = 'masks_from_surface'):
    """Creates EPI space masks from surface labels
    Requires fsl and freesurfer tools
    Parameters
    ----------
    name : string
        name of workflow
    Example
    -------
    >>> masks_from_surface = create_masks_from_surface_workflow('masks_from_surface', use_FS = True)
    >>> masks_from_surface.inputs.inputspec.EPI_space_file = 'example_func.nii.gz'
    >>> masks_from_surface.inputs.inputspec.label_directory = 'retmap'
    >>> masks_from_surface.inputs.inputspec.freesurfer_subject_ID = 'sub_01'
    >>> masks_from_surface.inputs.inputspec.freesurfer_subject_dir = '$SUBJECTS_DIR'
 
    Inputs::
          inputspec.EPI_space_file : EPI session file
          inputspec.reg_file : EPI session registration file
          inputspec.fill_thresh :  label2vol fill threshold argument
          inputspec.freesurfer_subject_ID : FS subject ID
          inputspec.freesurfer_subject_dir : $SUBJECTS_DIR
          inputspec.label_directory : directory that contains the labels in 'label'
          inputspec.output_directory : output directory in which a subfolder 
                                        with the name of label_directory is placed.
    Outputs::
           outputspec.output_masks : the output masks that are created.
           outputspec.EPI_T1_matrix_file : FLIRT registration file that maps EPI space to T1
           outputspec.T1_EPI_matrix_file : FLIRT registration file that maps T1 space to EPI
    """
    ### NODES
    input_node = pe.Node(IdentityInterface(
        fields=['EPI_space_file', 
        'output_directory', 
        'freesurfer_subject_ID', 
        'freesurfer_subject_dir', 
        'label_directory', 
        'reg_file', 
        'fill_thresh']), name='inputspec')
    output_node = pe.Node(IdentityInterface(fields=('output_masks')), name='outputspec')

    # housekeeping function for finding label files in FS directory
    def FS_label_list(freesurfer_subject_ID, freesurfer_subject_dir, label_directory):
        import glob
        import os.path as op

        label_list = glob.glob(op.join(freesurfer_subject_dir, freesurfer_subject_ID, 'label', label_directory, re)))

        return label_list

    FS_label_list_node = pe.Node(Function(input_names=('freesurfer_subject_ID', 'freesurfer_subject_dir', 'label_directory', 're'), output_names='label_list',
                                     function=FS_label_list), name='FS_label_list_node')  

    label_2_vol_node = pe.MapNode(interface=freesurfer.Label2Vol(), name='all_labels',
                                iterfield = 'label_file')
    binvol = MapNode(
        Label2Vol(label_file='cortex.label', fill_thresh=0.5, vol_label_file='foo_out.nii')


    ########################################################################################
    # actual workflow
    ########################################################################################

    masks_from_surface_workflow = pe.Workflow(name=name)

    masks_from_surface_workflow.connect(input_node, 'freesurfer_subject_ID', FS_label_list_node, 'freesurfer_subject_ID')    
    masks_from_surface_workflow.connect(input_node, 'freesurfer_subject_dir', FS_label_list_node, 'freesurfer_subject_dir')
    masks_from_surface_workflow.connect(input_node, 'label_directory', FS_label_list_node, 'label_directory')

    masks_from_surface_workflow.connect(input_node, 'reg_file', label_2_vol_node, 'reg_file')
    masks_from_surface_workflow.connect(input_node, 'EPI_space_file', label_2_vol_node, 'template')
    masks_from_surface_workflow.connect(input_node, 'fill_thresh', label_2_vol_node, 'fill_thresh')

    masks_from_surface_workflow.connect(input_node, 'freesurfer_subject_dir', label_2_vol_node, 'subjects_dir')
    masks_from_surface_workflow.connect(input_node, 'freesurfer_subject_ID', label_2_vol_node, 'subject_id')

    masks_from_surface_workflow.connect(label_2_vol_node, 'vol_label_file', output_node, 'output_masks')

    ########################################################################################
    # outputs via datasink
    ########################################################################################
    datasink = pe.Node(nio.DataSink(), name='sinker')

    # first link the workflow's output_directory into the datasink.
    masks_from_surface_workflow.connect(input_node, 'output_directory', datasink, 'base_directory')
    # and the rest
    masks_from_surface_workflow.connect(label_2_vol_node, 'vol_label_file', datasink, 'masks')

    return masks_from_surface_workflow

