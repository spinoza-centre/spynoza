import os.path as op
import nipype.pipeline as pe
from nipype.interfaces import fsl
from nipype.interfaces import freesurfer


def create_epi_to_T1_workflow(name = 'epi_to_T1'):
  """Registers session's EPI space to subject's T1 space
  uses either FLIRT or, when a FS segmentation is present, BBRegister
    Requires fsl and freesurfer tools
    Parameters
    ----------
    name : string
        name of workflow
    Example
    -------
    >>> epi_to_T1 = create_epi_to_T1_workflow()
    >>> epi_to_T1.inputs.inputspec.output_directory = '/data/project/raw/BIDS/sj_1/'
    >>> epi_to_T1.inputs.inputspec.EPI_space_file = 'example_Func.nii.gz'
    >>> epi_to_T1.inputs.inputspec.T1_file = 'T1.nii.gz'
    >>> epi_to_T1.inputs.inputspec.freesurfer_subject_ID = 'sub_01'
    >>> epi_to_T1.inputs.inputspec.freesurfer_subject_dir = '$SUBJECTS_DIR'
 
    Inputs::
          inputspec.output_directory : directory in which to sink the result files
          inputspec.T1_file : T1 anatomy file
          inputspec.EPI_space_file : EPI session file
          inputspec.freesurfer_subject_ID : FS subject ID
          inputspec.freesurfer_subject_dir : $SUBJECTS_DIR
    Outputs::
           outputspec.out_reg_file : BBRegister registration file that maps EPI space to T1
           outputspec.out_matrix_file : FLIRT registration file that maps EPI space to T1
           outputspec.out_inv_matrix_file : FLIRT registration file that maps T1 space to EPI
    """
  ### NODES
  input_node = pe.Node(IdentityInterface(
      fields=['EPI_space_file', 'output_directory', 'freesurfer_subject_ID', 'freesurfer_subject_dir', 'T1_file']), name='inputnode')

  # still have to choose which of these two output methods to use.

  datasink = pe.Node(nio.DataSink(), name='sinker')
  output_node = pe.Node(IdentityInterface(fields=('out_inv_matrix_file', 'out_matrix_file', 'out_reg_file')), name='outputnode')


  epi_to_T1_workflow = pe.Workflow(name='epi_to_T1')

  # first link the workflow's output_directory into the datasink.
  epi_to_T1_workflow.connect(input_node, 'output_directory', datasink, 'base_directory')
  epi_to_T1_workflow.connect(input_node, 'EPI_space_file', datasink, 'reg.feat.example_func.@nii.@gz')


  if freesurfer_subject_ID is not '': # do BBRegister if no SJ ID
    bbregister_N = pe.Node(freesurfer.BBRegister(init = 'fsl', contast_type = 't2' ), 
                          name = 'bbregister_N')

    epi_to_T1_workflow.connect(input_node, 'EPI_space_file', bbregister_N, 'source_file')
    epi_to_T1_workflow.connect(input_node, 'freesurfer_subject_ID', bbregister_N, 'subject_id')
    epi_to_T1_workflow.connect(input_node, 'freesurfer_subject_dir', bbregister_N, 'subjects_dir')
    epi_to_T1_workflow.connect(input_node, 'freesurfer_subject_dir', bbregister_N, 'subjects_dir')

    # epi_to_T1_workflow.connect(bbregister_N, 'out_fsl_file', datasink, FSL_REG_FILENAME)
    # epi_to_T1_workflow.connect(bbregister_N, 'out_reg_file', datasink, BBRegister_REG_FILENAME)

    epi_to_T1_workflow.connect(bbregister_N, 'out_fsl_file', output_node, 'out_matrix_file')
    epi_to_T1_workflow.connect(bbregister_N, 'out_reg_file', output_node, 'out_reg_file')

    # the final invert node
    invert_N = pe.Node(fsl.ConvertXFM(invert_xfm = True), name = 'invert_N')
    epi_to_T1_workflow.connect(bbregister_N, 'out_fsl_file', invert_N, 'in_file')
    epi_to_T1_workflow.connect(invert_N, 'out_file', output_node, 'out_inv_matrix_file')

    # and, datasink.
    epi_to_T1_workflow.connect(bbregister_N, 'out_fsl_file', datasink, 'reg.feat.example_func2highres.@mat')
    epi_to_T1_workflow.connect(invert_N, 'out_file', datasink, 'reg.feat.highres2example_func.@mat')
    epi_to_T1_workflow.connect(bbregister_N, 'out_reg_file', datasink, 'reg.register')


  else: # do flirt
    flirt_N = pe.Node(fsl.FLIRT(cost_func='bbr', output_type = 'NIFTI_GZ', dof = 12, interp = 'sinc'), 
                          name = 'flirt_N')
    epi_to_T1_workflow.connect(input_node, 'EPI_space_file', flirt_N, 'in_file')
    epi_to_T1_workflow.connect(input_node, 'T1_file', flirt_N, 'reference')
    epi_to_T1_workflow.connect(input_node, 'EPI_space_file', flirt_N, 'in_file')

    # epi_to_T1_workflow.connect(flirt_N, 'out_matrix_file', datasink, FSL_REG_FILENAME)

    epi_to_T1_workflow.connect(flirt_N, 'out_matrix_file', output_node, 'out_matrix_file')

    # the final invert node
    invert_N = pe.Node(fsl.ConvertXFM(invert_xfm = True), name = 'invert_N')
    epi_to_T1_workflow.connect(flirt_N, 'out_matrix_file', invert_N, 'in_file')
    epi_to_T1_workflow.connect(invert_N, 'out_file', output_node, 'out_inv_matrix_file')

    epi_to_T1_workflow.connect(flirt_N, 'out_matrix_file', datasink, 'reg.feat.example_func2highres.@mat')
    epi_to_T1_workflow.connect(invert_N, 'out_file', datasink, 'reg.feat.highres2example_func.@mat')

  return epi_to_T1_workflow

if __name__ == '__main__':

  pass