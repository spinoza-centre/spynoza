import os.path as op
import nipype.pipeline as pe
from nipype.interfaces import fsl
from nipype.interfaces import freesurfer


FSL_REG_FILENAME = 'register_fsl.mat'
BBRegister_REG_FILENAME = 'register.dat'

### NODES
input_node = pe.Node(IdentityInterface(
    fields=['EPI_space_file', 'output_directory', 'freesurfer_subject_ID', 'freesurfer_subject_dir', 'T1_file']), name='inputnode')

output_node = pe.Node(IdentityInterface(fields='out_file'), name='outputnode')

get_info = pe.Node(Function(input_names='in_file', output_names=['TR', 'shape', 'dyns', 'voxsize', 'affine'],
                          function=get_scaninfo), name='get_scaninfo')

datasink = pe.Node(nio.DataSink(input_names=['output_directory']]), name='sinker')

# ### household functions
# def create_fsl_mat_filename(base_directory):
#     return os.path.join(base_directory, FSL_REG_FILENAME)

# # and their nodes
# create_fsl_mat_filename_node = pe.Node(Function(input_names='base_directory', output_names='fsl_reg_file',
#                                    function=create_fsl_mat_filename), name='create_fsl_mat_filename_node')

epi_to_T1_workflow = pe.Workflow(name='epi_to_T1')

# first link the workflow's output_directory into the datasink.
epi_to_T1_workflow.connect(input_node, 'output_directory', datasink, 'base_directory')


if freesurfer_subject_ID not is '': # do BBRegister
  bbregister_N = pe.Node(freesurfer.BBRegister(init = 'fsl', contast_type = 't2' ), 
                        name = 'bbregister_N')

  epi_to_T1_workflow.connect(input_node, 'EPI_space_file', bbregister_N, 'source_file')
  epi_to_T1_workflow.connect(input_node, 'freesurfer_subject_ID', bbregister_N, 'subject_id')
  epi_to_T1_workflow.connect(input_node, 'freesurfer_subject_dir', bbregister_N, 'subjects_dir')
  epi_to_T1_workflow.connect(input_node, 'freesurfer_subject_dir', bbregister_N, 'subjects_dir')

  epi_to_T1_workflow.connect(bbregister_N, 'out_fsl_file', datasink, FSL_REG_FILENAME)
  epi_to_T1_workflow.connect(bbregister_N, 'out_reg_file', datasink, BBRegister_REG_FILENAME)


else: # do flirt
  flirt_N = pe.Node(fsl.FLIRT(cost_func='bbr', output_type = 'NIFTI_GZ', dof = 12, interp = 'sinc'), 
                        name = 'flirt_N')
  epi_to_T1_workflow.connect(input_node, 'EPI_space_file', flirt_N, 'in_file')
  epi_to_T1_workflow.connect(input_node, 'T1_file', flirt_N, 'reference')
  epi_to_T1_workflow.connect(input_node, 'EPI_space_file', flirt_N, 'in_file')
  epi_to_T1_workflow.connect(flirt_N, 'out_matrix_file', datasink, FSL_REG_FILENAME)


if __name__ == '__main__':

  pass