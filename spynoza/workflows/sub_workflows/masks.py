import os.path as op
import glob
import nipype.pipeline as pe
from nipype.interfaces import fsl
from nipype.interfaces import freesurfer
from nipype.interfaces.utility import Function, IdentityInterface

def create_transform_aseg_to_EPI_workflow(name = 'transform_aseg_to_EPI'):
    """Transforms freesurfer volume-aseg to EPI space and dumps it in the masks folder
    Requires fsl and freesurfer tools
    Parameters
    ----------
    name : string
        name of workflow
    Example
    -------
    >>> masks_from_surface = create_transform_aseg_to_EPI_workflow('transform_aseg_to_EPI')
    >>> masks_from_surface.inputs.inputspec.EPI_space_file = 'example_func.nii.gz'
    >>> masks_from_surface.inputs.inputspec.label_directory = 'retmap'
    >>> masks_from_surface.inputs.inputspec.freesurfer_subject_ID = 'sub_01'
    >>> masks_from_surface.inputs.inputspec.freesurfer_subject_dir = '$SUBJECTS_DIR'
    >>> masks_from_surface.inputs.inputspec.aseg =  'aparc.a2009s+aseg.mgz'

 
    Inputs::
          inputspec.EPI_space_file : EPI session file
          inputspec.reg_file : EPI session registration file
          inputspec.re : regular expression for the 
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
        'aseg', 
        'reg_file']), name='inputspec')
    output_node = pe.Node(IdentityInterface(fields=('output_mask')), name='outputspec')

    vol_trans_node = pe.Node(interface=freesurfer.ApplyVolTransform(), name='vol_trans')

    # housekeeping function for finding T1 file in FS directory
    def FS_aseg_file(freesurfer_subject_ID, freesurfer_subject_dir, aseg):
        return op.join(freesurfer_subject_dir, freesurfer_subject_ID, 'mri', aseg)

    FS_aseg_file_node = pe.Node(Function(input_names=('freesurfer_subject_ID', 'freesurfer_subject_dir'), output_names='aseg_mgz_path',
                                 function=FS_aseg_file), name='FS_aseg_file_node')  

    mriConvert_N = pe.Node(freesurfer.MRIConvert(out_type = 'nii.gz'), 
                          name = 'mriConvert_N')

    ########################################################################################
    # actual workflow
    ########################################################################################

    transform_aseg_to_EPI_workflow = pe.Workflow(name=name)

    transform_aseg_to_EPI_workflow.connect(input_node, 'freesurfer_subject_ID', FS_aseg_file_node, 'freesurfer_subject_ID')
    transform_aseg_to_EPI_workflow.connect(input_node, 'freesurfer_subject_dir', FS_aseg_file_node, 'freesurfer_subject_dir')
    transform_aseg_to_EPI_workflow.connect(input_node, 'aseg', FS_aseg_file_node, 'aseg')

    transform_aseg_to_EPI_workflow.connect(FS_T1_file_node, 'aseg_mgz_path', vol_trans_node, 'source_file')
    transform_aseg_to_EPI_workflow.connect(input_node, 'reg_file', vol_trans_node, 'reg_file')    

    transform_aseg_to_EPI_workflow.connect(vol_trans_node, 'transformed_file', mriConvert_N, 'in_file')
    transform_aseg_to_EPI_workflow.connect(mriConvert_N, 'out_file', output_node, 'output_mask')

    ########################################################################################
    # outputs via datasink
    ########################################################################################
    datasink = pe.Node(nio.DataSink(), name='sinker')

    # first link the workflow's output_directory into the datasink.
    transform_aseg_to_EPI_workflow.connect(input_node, 'output_directory', datasink, 'base_directory')
    # and the rest
    transform_aseg_to_EPI_workflow.connect(mriConvert_N, 'out_file', datasink, 'masks')

    return transform_aseg_to_EPI_workflow



def create_transform_atlas_to_EPI_workflow(name = 'transform_atlas_to_EPI'):
    """Transforms MNI-based volume-atlas to EPI space and dumps it in the masks folder.
    As this does not split up the file according to the values, this will work also for 
    MNI-based single ROI definitions.
    Requires fsl tools
    Parameters
    ----------
    name : string
        name of workflow
    Example
    -------
    >>> masks_from_surface = create_transform_aseg_to_EPI_workflow('transform_aseg_to_EPI')
    >>> masks_from_surface.inputs.inputspec.EPI_space_file = 'example_func.nii.gz'
    >>> masks_from_surface.inputs.inputspec.output_directory = full path to opd
    >>> masks_from_surface.inputs.inputspec.output_filename = 'mni_harvard_oxford'
    >>> masks_from_surface.inputs.inputspec.atlas =  '/usr/local/fsl/data/atlases/HarvardOxford/HarvardOxford-sub-maxprob-thr50-2mm.nii.gz'
    >>> masks_from_surface.inputs.inputspec.reg_file =  full path to opd /reg/feat/standard2example_func.mat

 
    Inputs::
          inputspec.EPI_space_file : EPI session file
          inputspec.reg_file : standard2example_func.mat
          inputspec.output_directory : output directory in which a subfolder 
                                        with the name of label_directory is placed.
          inputspec.output_filename : output filename
          inputspec.atlas : full path to atlas file
    Outputs::
           outputspec.output_mask : the output masks that are created.
    """
    ### NODES
    input_node = pe.Node(IdentityInterface(
        fields=['EPI_space_file', 
        'output_directory', 
        'output_filename', 
        'atlas', 
        'reg_file']), name='inputspec')
    output_node = pe.Node(IdentityInterface(fields=('output_mask')), name='outputspec')

    vol_trans_node = pe.Node(interface=fsl.ApplyXfm(apply_xfm = True, interp = 'sinc'), name='vol_trans')

    ########################################################################################
    # actual workflow
    ########################################################################################

    transform_atlas_to_EPI_workflow = pe.Workflow(name=name)

    transform_atlas_to_EPI_workflow.connect(input_node, 'atlas', vol_trans_node, 'in_file')
    transform_atlas_to_EPI_workflow.connect(input_node, 'reg_file', vol_trans_node, 'in_matrix_file')
    transform_atlas_to_EPI_workflow.connect(input_node, 'EPI_space_file', vol_trans_node, 'reference')

    transform_atlas_to_EPI_workflow.connect(vol_trans_node, 'out_file', output_node, 'output_mask')

    ########################################################################################
    # outputs via datasink
    ########################################################################################
    datasink = pe.Node(nio.DataSink(), name='sinker')

    # first link the workflow's output_directory into the datasink.
    transform_aseg_to_EPI_workflow.connect(input_node, 'output_directory', datasink, 'base_directory')
    # and the rest
    transform_aseg_to_EPI_workflow.connect(vol_trans_node, 'out_file', datasink, 'masks')

    return transform_aseg_to_EPI_workflow


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
          inputspec.re : regular expression for the 
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
        'fill_thresh',
        're']), name='inputspec')
    output_node = pe.Node(IdentityInterface(fields=('output_masks')), name='outputspec')

    # housekeeping function for finding label files in FS directory
    def FS_label_list(freesurfer_subject_ID, freesurfer_subject_dir, label_directory, re):
        import glob
        import os.path as op

        label_list = glob.glob(op.join(freesurfer_subject_dir, freesurfer_subject_ID, 'label', label_directory, re))

        return label_list

    FS_label_list_node = pe.Node(Function(input_names=('freesurfer_subject_ID', 'freesurfer_subject_dir', 'label_directory', 're'), output_names='label_list',
                                     function=FS_label_list), name='FS_label_list_node')

    label_2_vol_node = pe.MapNode(interface=freesurfer.Label2Vol(), name='all_labels',
                                iterfield = 'label_file')

    ########################################################################################
    # actual workflow
    ########################################################################################

    masks_from_surface_workflow = pe.Workflow(name=name)

    masks_from_surface_workflow.connect(input_node, 'freesurfer_subject_ID', FS_label_list_node, 'freesurfer_subject_ID')    
    masks_from_surface_workflow.connect(input_node, 'freesurfer_subject_dir', FS_label_list_node, 'freesurfer_subject_dir')
    masks_from_surface_workflow.connect(input_node, 'label_directory', FS_label_list_node, 'label_directory')
    masks_from_surface_workflow.connect(input_node, 're', FS_label_list_node, 're')

    masks_from_surface_workflow.connect(input_node, 'reg_file', label_2_vol_node, 'reg_file')
    masks_from_surface_workflow.connect(input_node, 'EPI_space_file', label_2_vol_node, 'template')
    masks_from_surface_workflow.connect(input_node, 'fill_thresh', label_2_vol_node, 'fill_thresh')

    masks_from_surface_workflow.connect(input_node, 'freesurfer_subject_dir', label_2_vol_node, 'subjects_dir')
    masks_from_surface_workflow.connect(input_node, 'freesurfer_subject_ID', label_2_vol_node, 'subject_id')

    # and the iter field filled in from the label collection node
    masks_from_surface_workflow.connect(FS_label_list_node, 'label_list', label_2_vol_node, 'label_file')

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



def create_fast2mask_workflow(name = 'fast2mask'):
    """Performs tissue segmentation FSL-Fast from T1, and transforms the resulting
    masks to EPI space masks
    Requires fsl
    Parameters
    ----------
    name : string
        name of workflow
    Example
    -------
    >>> masks_from_surface = create_fast2mask_workflow('fast2mask')
    >>> masks_from_surface.inputs.inputspec.EPI_space_file = 'example_func.nii.gz'
    >>> masks_from_surface.inputs.inputspec.anatomical_file = 'retmap'
    >>> masks_from_surface.inputs.inputspec.output_directory = 'sub_01'
    >>> masks_from_surface.inputs.inputspec.registration_matrix_file = 'highres2example_func.nii.gz'
 
    Inputs::
          inputspec.EPI_space_file : EPI session file
          inputspec.anatomical_file : EPI session registration file
          inputspec.registration_matrix_file :  FSL style registration matrix, from anatomical to EPI space
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
        'anatomical_file',
        'output_directory', 
        'registration_matrix_file']), name='inputspec')
    output_node = pe.Node(IdentityInterface(fields=('output_masks')), name='outputspec')

    fast_node = pe.Node(interface=fsl.FAST(img_type = 1), name='fast')

    ########################################################################################
    # actual workflow
    ########################################################################################

    fast2mask_workflow = pe.Workflow(name=name)

    fast2mask_workflow.connect(ipnut_node, 'anatomical_file', fast_node, 'in_files')



    masks_from_surface_workflow.connect(input_node, 'freesurfer_subject_ID', FS_label_list_node, 'freesurfer_subject_ID')    
    masks_from_surface_workflow.connect(input_node, 'freesurfer_subject_dir', FS_label_list_node, 'freesurfer_subject_dir')
    masks_from_surface_workflow.connect(input_node, 'label_directory', FS_label_list_node, 'label_directory')
    masks_from_surface_workflow.connect(input_node, 're', FS_label_list_node, 're')

    masks_from_surface_workflow.connect(input_node, 'reg_file', label_2_vol_node, 'reg_file')
    masks_from_surface_workflow.connect(input_node, 'EPI_space_file', label_2_vol_node, 'template')
    masks_from_surface_workflow.connect(input_node, 'fill_thresh', label_2_vol_node, 'fill_thresh')

    masks_from_surface_workflow.connect(input_node, 'freesurfer_subject_dir', label_2_vol_node, 'subjects_dir')
    masks_from_surface_workflow.connect(input_node, 'freesurfer_subject_ID', label_2_vol_node, 'subject_id')

    # and the iter field filled in from the label collection node
    masks_from_surface_workflow.connect(FS_label_list_node, 'label_list', label_2_vol_node, 'label_file')

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