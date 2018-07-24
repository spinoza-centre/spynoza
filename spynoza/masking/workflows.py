import nipype.pipeline as pe
import nipype.interfaces.io as nio
from nipype.interfaces import fsl
from nipype.interfaces import freesurfer
from nipype.interfaces.utility import IdentityInterface, Merge
from .nodes import FS_aseg_file, FS_LabelNode


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
    FS_aseg_file_node = pe.Node(interface=FS_aseg_file,
                                name='FS_aseg_file')
    mriConvert_N = pe.Node(freesurfer.MRIConvert(out_type = 'nii.gz'), 
                          name = 'mriConvert_N')

    ########################################################################################
    # actual workflow
    ########################################################################################

    transform_aseg_to_EPI_workflow = pe.Workflow(name=name)

    transform_aseg_to_EPI_workflow.connect(input_node, 'freesurfer_subject_ID', FS_aseg_file_node, 'freesurfer_subject_ID')
    transform_aseg_to_EPI_workflow.connect(input_node, 'freesurfer_subject_dir', FS_aseg_file_node, 'freesurfer_subject_dir')
    transform_aseg_to_EPI_workflow.connect(input_node, 'aseg', FS_aseg_file_node, 'aseg')

    transform_aseg_to_EPI_workflow.connect(FS_aseg_file_node, 'aseg_mgz_path', vol_trans_node, 'source_file')
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
    >>> transform_atlas_to_EPI = create_transform_aseg_to_EPI_workflow('transform_aseg_to_EPI')
    >>> transform_atlas_to_EPI.inputs.inputspec.EPI_space_file = 'example_func.nii.gz'
    >>> transform_atlas_to_EPI.inputs.inputspec.output_directory = full path to opd
    >>> transform_atlas_to_EPI.inputs.inputspec.output_filename = 'mni_harvard_oxford'
    >>> transform_atlas_to_EPI.inputs.inputspec.atlas =  '/usr/local/fsl/data/atlases/HarvardOxford/HarvardOxford-sub-maxprob-thr50-2mm.nii.gz'
    >>> transform_atlas_to_EPI.inputs.inputspec.reg_file =  full path to opd /reg/feat/standard2example_func.mat

 
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
    import os.path as op
    import glob
    import nipype.pipeline as pe
    from nipype.interfaces import fsl
    from nipype.interfaces import freesurfer
    from nipype.interfaces.utility import Function, IdentityInterface, Merge
    import nipype.interfaces.io as nio

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
    transform_atlas_to_EPI_workflow.connect(input_node, 'output_directory', datasink, 'base_directory')
    # and the rest
    transform_atlas_to_EPI_workflow.connect(vol_trans_node, 'out_file', datasink, 'roi.atlas')

    return transform_atlas_to_EPI_workflow


def create_masks_from_surface_workflow(name = 'masks_from_surface'):
    """Creates EPI space masks from surface labels
    Requires fsl and freesurfer tools
    Parameters
    ----------
    name : string
        name of workflow
    Example
    -------
    >>> masks_from_surface = create_masks_from_surface_workflow('masks_from_surface')
    >>> masks_from_surface.inputs.inputspec.EPI_space_file = 'example_func.nii.gz'
    >>> masks_from_surface.inputs.inputspec.label_directory = 'retmap'
    >>> masks_from_surface.inputs.inputspec.freesurfer_subject_ID = 'sub_01'
    >>> masks_from_surface.inputs.inputspec.freesurfer_subject_dir = '$SUBJECTS_DIR'
    
    from spynoza.workflows.sub_workflows.masks import create_masks_from_surface_workflow
    mfs = create_masks_from_surface_workflow(name = 'mfs')
    mfs.inputs.inputspec.freesurfer_subject_dir = '/home/raw_data/-2014/reward/human_reward/data/FS_SJID'
    mfs.inputs.inputspec.label_directory = 'retmap'
    mfs.inputs.inputspec.EPI_space_file = '/home/shared/-2014/reward/new/sub-002/reg/example_func.nii.gz'
    mfs.inputs.inputspec.output_directory = '/home/shared/-2014/reward/new/sub-002/masks/'
    mfs.inputs.inputspec.freesurfer_subject_ID = 'sub-002'
    mfs.inputs.inputspec.reg_file = '/home/shared/-2014/reward/new/sub-002/reg/register.dat'
    mfs.inputs.inputspec.fill_thresh = 0.01
    mfs.inputs.inputspec.re = '*.label'
    mfs.run('MultiProc', plugin_args={'n_procs': 32})


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
    """
    ### NODES
    import nipype.pipeline as pe
    from nipype.interfaces.utility import Function, IdentityInterface, Merge
    import nipype.interfaces.io as nio
    import nipype.interfaces.utility as niu
    import os.path as op
    from .nodes import FS_label_list_glob_node
    
    input_node = pe.Node(IdentityInterface(
        fields=['EPI_space_file', 
        'output_directory', 
        'freesurfer_subject_ID', 
        'freesurfer_subject_dir', 
        'label_directory', 
        'reg_file', 
        'fill_thresh',
        're']), name='inputspec')
    output_node = pe.Node(IdentityInterface(fields=([
        'masks'])), name='outputspec')

    # housekeeping function for finding label files in FS directory
    FS_label_list_node = pe.Node(interface=FS_LabelNode,
                                 name='FS_label_list_node')

    label_2_vol_node = pe.MapNode(interface=freesurfer.Label2Vol(), name='l2v',
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
    masks_from_surface_workflow.connect(input_node, 'EPI_space_file', label_2_vol_node, 'template_file')
    masks_from_surface_workflow.connect(input_node, 'fill_thresh', label_2_vol_node, 'fill_thresh')

    masks_from_surface_workflow.connect(input_node, 'freesurfer_subject_dir', label_2_vol_node, 'subjects_dir')
    masks_from_surface_workflow.connect(input_node, 'freesurfer_subject_ID', label_2_vol_node, 'subject_id')

    # and the iter field filled in from the label collection node
    masks_from_surface_workflow.connect(FS_label_list_node, 'label_list', label_2_vol_node, 'label_file')

    ########################################################################################
    # outputs via datasink
    ########################################################################################
    datasink = pe.Node(nio.DataSink(), name='sinker')
    datasink.inputs.parameterization = False

    # first link the workflow's output_directory into the datasink.
    masks_from_surface_workflow.connect(input_node, 'output_directory', datasink, 'base_directory')

    masks_from_surface_workflow.connect(label_2_vol_node, 'vol_label_file', datasink, 'roi')
    masks_from_surface_workflow.connect(label_2_vol_node, 'vol_label_file', output_node, 'masks')

    return masks_from_surface_workflow



def create_fast2mask_workflow(name = 'fast2mask'):
    """Performs tissue segmentation FSL-Fast from T1, and transforms the resulting
    masks to EPI space masks. Assumes T1 anatomical for now.
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
    output_node = pe.Node(IdentityInterface(fields=('out_files')), name='outputspec')

    fast_node = pe.Node(interface=fsl.FAST(img_type = 1, probability_maps = True), name='fast')

    fast_output_merge_node = pe.Node(Merge(2), infields = ['bin', 'prob'])

    apply_xfm_node = pe.MapNode(fsl.ApplyXfm(apply_xfm = True), iterfield = ['in_file'])

    ########################################################################################
    # actual workflow
    ########################################################################################

    fast2mask_workflow = pe.Workflow(name=name)

    fast2mask_workflow.connect(input_node, 'anatomical_file', fast_node, 'in_files')

    fast2mask_workflow.connect(fast_node, 'probability_maps', fast_output_merge_node, 'prob')
    fast2mask_workflow.connect(fast_node, 'tissue_class_files', fast_output_merge_node, 'bin')

    fast2mask_workflow.connect(fast_output_merge_node, 'out_files', apply_xfm_node, 'in_file')
    fast2mask_workflow.connect(input_node, 'registration_matrix_file', apply_xfm_node, 'in_matrix_file')
    fast2mask_workflow.connect(input_node, 'EPI_space_file', apply_xfm_node, 'reference')

    fast2mask_workflow.connect(apply_xfm_node, 'out_file', output_node, 'out_files')

   ########################################################################################
    # outputs via datasink
    ########################################################################################
    datasink = pe.Node(nio.DataSink(), name='sinker')
    datasink.inputs.parameterization = False

    # first link the workflow's output_directory into the datasink.
    fast2mask_workflow.connect(input_node, 'output_directory', datasink, 'base_directory')
    fast2mask_workflow.connect(input_node, 'sub_id', datasink, 'container')
    # and the rest
    fast2mask_workflow.connect(apply_xfm_node, 'out_file', datasink, 'masks.fast')

    return fast2mask_workflow
