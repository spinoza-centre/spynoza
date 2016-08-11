import os.path as op
import nipype.pipeline as pe
from nipype.interfaces import fsl
from nipype.interfaces import freesurfer



def create_concat_2_feat_workflow(name = 'concat_2_feat'):
    """Concatenates and inverts previously created fsl mat registration files.
    Requires fsl tools
    Parameters
    ----------
    name : string
        name of workflow
    Example
    -------
    >>> concat_2_feat = create_concat_2_feat_workflow()
    >>> concat_2_feat.inputs.inputspec.output_directory = '/data/project/raw/BIDS/sj_1/'
    >>> concat_2_feat.inputs.inputspec.T1_file = 'T1.nii.gz'
    >>> concat_2_feat.inputs.inputspec.reference_file = 'MNI.nii.gz'
    >>> concat_2_feat.inputs.inputspec.EPI_space_file = 'EPI.nii.gz'
    >>> concat_2_feat.inputs.inputspec.T1_MNI_matrix_file = 'highres2standard.mat'
    >>> concat_2_feat.inputs.inputspec.MNI_T1_matrix_file = 'standard2highres.mat'
    >>> concat_2_feat.inputs.inputspec.EPI_T1_matrix_file = 'example_func2highres.mat'
    >>> concat_2_feat.inputs.inputspec.T1_EPI_matrix_file = 'highres2example_func.mat'

    Inputs::
          inputspec.output_directory : directory in which to sink the result files
          inputspec.T1_file : T1 anatomy file
          inputspec.reference_file : MNI standard file
          inputspec.EPI_space_file : EPI standard file
          inputspec.T1_MNI_matrix_file : SE
          inputspec.MNI_T1_matrix_file : SE
          inputspec.EPI_T1_matrix_file : SE
          inputspec.T1_EPI_matrix_file : SE
    Outputs::
           outputspec.MNI_EPI_matrix_file : registration file that maps standard image to
                                 EPI space
           outputspec.EPI_MNI_matrix_file : registration file that maps EPI image to
                                 standard space
    """

  ### NODES
  input_node = pe.Node(IdentityInterface(
      fields=['output_directory', 'T1_file', 'reference_file', 'EPI_space_file', 
              'T1_MNI_matrix_file', 'MNI_T1_matrix_file', 'EPI_T1_matrix_file', 'T1_EPI_matrix_file'
      ]), name='inputnode')

  # still have to choose which of these two output methods to use.

  datasink = pe.Node(nio.DataSink(), name='sinker')
  output_node = pe.Node(IdentityInterface(fields='out_file'), name='outputnode')

  concat_2_feat_workflow = pe.Workflow(name=name)

  # first link the workflow's output_directory into the datasink.
  concat_2_feat_workflow.connect(input_node, 'output_directory', datasink, 'base_directory')

  ########################################################################################
  # concat step, from EPI to T1 to MNI
  ########################################################################################
  concat_N = pe.Node(fsl.ConvertXFM(concat_xfm = True), name = 'invert_N')
  concat_2_feat_workflow.connect(input_node, 'EPI_T1_matrix_file', concat_N, 'in_file')
  concat_2_feat_workflow.connect(input_node, 'T1_MNI_matrix_file', concat_N, 'in_file2')
  concat_2_feat_workflow.connect(concat_N, 'out_file', output_node, 'EPI_MNI_matrix_file')
  concat_2_feat_workflow.connect(concat_N, 'out_file', datasink, 'reg.example_func2standard.@mat')


  ########################################################################################
  # invert step, to go from MNI to T1 to EPI
  ########################################################################################
  invert_N = pe.Node(fsl.ConvertXFM(invert_xfm = True), name = 'invert_N')
  concat_2_feat_workflow.connect(concat_N, 'out_file', invert_N, 'in_file')
  concat_2_feat_workflow.connect(invert_N, 'out_file', output_node, 'MNI_EPI_matrix_file')
  concat_2_feat_workflow.connect(invert_N, 'out_file', datasink, 'reg.standard2example_func.@mat')

  return concat_2_feat_workflow

if __name__ == '__main__':

  pass