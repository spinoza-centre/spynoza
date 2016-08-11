import os.path as op
import nipype.pipeline as pe
from nipype.interfaces import fsl
from nipype.interfaces import freesurfer
from nipype.utils.filemanip import copyfile


FSL_REG_FILENAME = 'register_fsl.mat'

### NODES
input_node = pe.Node(IdentityInterface(
    fields=['output_directory', 'T1_file', 'reference_file', 'EPI_space_file', 
            'T1_MNI_matrix_file', 'MNI_T1_matrix_file', 'EPI_T1_matrix_file', 'T1_EPI_matrix_file'
    ]), name='inputnode')

# still have to choose which of these two output methods to use.

datasink = pe.Node(nio.DataSink(), name='sinker')
output_node = pe.Node(IdentityInterface(fields='out_file'), name='outputnode')

concat_2_feat_workflow = pe.Workflow(name='concat_2_feat')

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


if __name__ == '__main__':

  pass