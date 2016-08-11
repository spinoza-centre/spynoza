import os.path as op
import nipype.pipeline as pe
from nipype.interfaces import fsl
from nipype.interfaces.utility import IdentityInterface
import nipype.interfaces.io as nio


def create_T1_to_MNI_workflow(name = 'T1_to_MNI'):
  """Registers subject's T1 to MNI space using FLIRT and FNIRT.
    Requires fsl tools
    Parameters
    ----------
    name : string
        name of workflow
    Example
    -------
    >>> T1_to_MNI = create_T1_to_MNI_workflow()
    >>> T1_to_MNI.inputs.inputspec.output_directory = '/data/project/raw/BIDS/sj_1/'
    >>> T1_to_MNI.inputs.inputspec.T1_file = 'T1.nii.gz'
    >>> T1_to_MNI.inputs.inputspec.reference_file = 'MNI.nii.gz'
    >>> T1_to_MNI.inputs.inputspec.freesurfer_subject_ID = 'sub_01'
    >>> T1_to_MNI.inputs.inputspec.freesurfer_subject_dir = '$SUBJECTS_DIR'
 
    Inputs::
          inputspec.output_directory : directory in which to sink the result files
          inputspec.T1_file : T1 anatomy file
          inputspec.reference_file : MNI standard file
          inputspec.freesurfer_subject_ID : FS subject ID
          inputspec.freesurfer_subject_dir : $SUBJECTS_DIR
    Outputs::
           outputspec.T1_MNI_file : T1 converted to MNI
           outputspec.out_matrix_file : mat file specifying how to convert T1 to MNI
           outputspec.out_inv_matrix_file : mat file specifying how to convert MNI to T1
           outputspec.warp_field_file : FNIRT warp field
           outputspec.warp_fieldcoeff_file : FNIRT warp coeff field
           outputspec.warped_file : FNIRT warped T1
           outputspec.out_intensitymap_file : FNIRT intensity map

    """

  ### NODES
  input_node = pe.Node(IdentityInterface(
      fields=['output_directory', 'freesurfer_subject_ID', 'freesurfer_subject_dir', 'T1_file', 'reference_file']), name='inputnode')

  # still have to choose which of these two output methods to use.

  datasink = pe.Node(nio.DataSink(), name='sinker')
  output_node = pe.Node(IdentityInterface(fields=['T1_MNI_file', 
                    'out_matrix_file', 
                    'out_inv_matrix_file',
                    'warp_field_file'
                    'warp_fieldcoeff_file',
                    'warped_file',
                    'modulatedref_file',
                    'out_intensitymap_file',
                    ]), name='outputnode')

  # housekeeping function for finding T1 file in FS directory
  def FS_T1_file(freesurfer_subject_ID, freesurfer_subject_dir):
    return op.join(freesurfer_subject_dir, freesurfer_subject_ID, 'orig', 'T1.mgz')

  FS_T1_file_node = pe.Node(Function(input_names=('freesurfer_subject_ID', 'freesurfer_subject_dir'), output_names='T1_mgz_path',
                                     function=FS_T1_file), name='FS_T1_file_node')  

  T1_to_MNI_workflow = pe.Workflow(name='T1_to_MNI')

  # first link the workflow's output_directory into the datasink.
  T1_to_MNI_workflow.connect(input_node, 'output_directory', datasink, 'base_directory')
  # and immediately attempt to datasink the standard file
  T1_to_MNI_workflow.connect(input_node, 'reference_file', datasink, 'reg.feat.standard.@nii.@gz')

  ########################################################################################
  # first take file from freesurfer subject directory, if necessary
  # in which case we assume that there is no T1_file at present and overwrite it
  ########################################################################################
  if freesurfer_subject_ID is not '': 
    mriConvert_N = pe.Node(freesurfer.MRIConvert(out_type = 'nii.gz'), 
                          name = 'mriConvert_N')

    T1_to_MNI_workflow.connect(input_node, 'freesurfer_subject_ID', FS_T1_file_node, 'freesurfer_subject_ID')
    T1_to_MNI_workflow.connect(input_node, 'freesurfer_subject_dir', FS_T1_file_node, 'freesurfer_subject_dir')

    T1_to_MNI_workflow.connect(FS_T1_file_node, 'T1_mgz_path', mriConvert_N, 'in_file')
    T1_to_MNI_workflow.connect(input_node, 'T1_file', mriConvert_N, 'out_file')

    T1_to_MNI_workflow.connect(mriConvert_N, 'out_file', datasink, 'reg.feat.highres.@nii.@gz')


  ########################################################################################
  # FLIRT step
  ########################################################################################
  flirt_N = pe.Node(fsl.FLIRT(cost_func='bbr', output_type = 'NIFTI_GZ', dof = 12, interp = 'sinc'), 
                        name = 'flirt_N')
  T1_to_MNI_workflow.connect(input_node, 'T1_file', flirt_N, 'in_file')
  T1_to_MNI_workflow.connect(input_node, 'reference_file', flirt_N, 'reference')
  T1_to_MNI_workflow.connect(input_node, 'EPI_space_file', flirt_N, 'in_file')

  T1_to_MNI_workflow.connect(flirt_N, 'out_matrix_file', output_node, 'out_matrix_file')
  T1_to_MNI_workflow.connect(flirt_N, 'out_file', output_node, 'T1_MNI_file')

  T1_to_MNI_workflow.connect(flirt_N, 'out_matrix_file', datasink, 'reg.feat.highres2standard.@mat')


  ########################################################################################
  # invert step
  ########################################################################################
  invert_N = pe.Node(fsl.ConvertXFM(invert_xfm = True), name = 'invert_N')
  T1_to_MNI_workflow.connect(flirt_N, 'out_matrix_file', invert_N, 'in_file')
  T1_to_MNI_workflow.connect(invert_N, 'out_file', output_node, 'out_inv_matrix_file')

  T1_to_MNI_workflow.connect(invert_N, 'out_file', datasink, 'reg.feat.standard2highres.@mat')


  ########################################################################################
  # FNIRT step
  ########################################################################################
  fnirt_N = pe.Node(fsl.FNIRT(in_fwhm = [8, 4, 2, 2], 
                              subsampling_scheme = [4, 2, 1, 1], 
                              warp_resolution = (6, 6, 6), 
                              output_type = 'NIFTI_GZ', 
                              interp = 'sinc'), 
                        name = 'fnirt_N')

  T1_to_MNI_workflow.connect(fnirt_N, 'affine_file', flirt_N, 'out_matrix_file')
  T1_to_MNI_workflow.connect(input_node, 'reference_file', fnirt_N, 'ref_file')

  T1_to_MNI_workflow.connect(fnirt_N, 'field_file', output_node, 'warp_field_file')
  T1_to_MNI_workflow.connect(fnirt_N, 'fieldcoeff_file', output_node, 'warp_fieldcoeff_file')
  T1_to_MNI_workflow.connect(fnirt_N, 'warped_file', output_node, 'warped_file')
  T1_to_MNI_workflow.connect(fnirt_N, 'modulatedref_file', output_node, 'modulatedref_file')
  T1_to_MNI_workflow.connect(fnirt_N, 'out_intensitymap_file', output_node, 'out_intensitymap_file')

  return T1_to_MNI_workflow

if __name__ == '__main__':

  pass