import os.path as op
import nipype.pipeline as pe
from nipype.interfaces import fsl
from nipype.interfaces import freesurfer


FSL_REG_FILENAME = 'register_fsl.mat'
BBRegister_REG_FILENAME = 'register.dat'

### NODES
input_node = pe.Node(IdentityInterface(
    fields=['EPI_space_file', 'output_directory', 'freesurfer_subject_ID', 'freesurfer_subject_dir', 'T1_file']), name='inputnode')

# still have to choose which of these two output methods to use.

# datasink = pe.Node(nio.DataSink(input_names=['output_directory']]), name='sinker')
output_node = pe.Node(IdentityInterface(fields='out_file'), name='outputnode')


epi_to_T1_workflow = pe.Workflow(name='epi_to_T1')

# first link the workflow's output_directory into the datasink.
epi_to_T1_workflow.connect(input_node, 'output_directory', datasink, 'base_directory')


if freesurfer_subject_ID not is '': # do BBRegister if no SJ ID
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


if __name__ == '__main__':

  pass