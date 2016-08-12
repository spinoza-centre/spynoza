import os.path as op
import nipype.pipeline as pe
from nipype.interfaces import fsl
from nipype.interfaces import freesurfer
from nipype.interfaces.utility import IdentityInterface
import nipype.interfaces.io as nio


def create_epi_to_T1_workflow(name = 'epi_to_T1', use_FS = True):
    """Registers session's EPI space to subject's T1 space
    uses either FLIRT or, when a FS segmentation is present, BBRegister
    Requires fsl and freesurfer tools
    Parameters
    ----------
    name : string
        name of workflow
    use_FS : bool
        whether to use freesurfer's segmentation and BBRegister
    Example
    -------
    >>> epi_to_T1 = create_epi_to_T1_workflow('epi_to_T1', use_FS = True)
    >>> epi_to_T1.inputs.inputspec.EPI_space_file = 'example_Func.nii.gz'
    >>> epi_to_T1.inputs.inputspec.T1_file = 'T1.nii.gz'
    >>> epi_to_T1.inputs.inputspec.freesurfer_subject_ID = 'sub_01'
    >>> epi_to_T1.inputs.inputspec.freesurfer_subject_dir = '$SUBJECTS_DIR'
 
    Inputs::
          inputspec.T1_file : T1 anatomy file
          inputspec.EPI_space_file : EPI session file
          inputspec.freesurfer_subject_ID : FS subject ID
          inputspec.freesurfer_subject_dir : $SUBJECTS_DIR
    Outputs::
           outputspec.EPI_T1_register_file : BBRegister registration file that maps EPI space to T1
           outputspec.EPI_T1_matrix_file : FLIRT registration file that maps EPI space to T1
           outputspec.T1_EPI_matrix_file : FLIRT registration file that maps T1 space to EPI
    """
    ### NODES
    input_node = pe.Node(IdentityInterface(
        fields=['EPI_space_file', 'output_directory', 'freesurfer_subject_ID', 'freesurfer_subject_dir', 'T1_file']), name='inputspec')

    output_node = pe.Node(IdentityInterface(fields=('EPI_T1_matrix_file', 'T1_EPI_matrix_file', 'EPI_T1_register_file')), name='outputspec')

    epi_to_T1_workflow = pe.Workflow(name='epi_to_T1')

    if use_FS: # do BBRegister if no SJ ID
        bbregister_N = pe.Node(freesurfer.BBRegister(init = 'fsl', contast_type = 't2' ),
                               name = 'bbregister_N')

        epi_to_T1_workflow.connect(input_node, 'EPI_space_file', bbregister_N, 'source_file')
        epi_to_T1_workflow.connect(input_node, 'freesurfer_subject_ID', bbregister_N, 'subject_id')
        epi_to_T1_workflow.connect(input_node, 'freesurfer_subject_dir', bbregister_N, 'subjects_dir')
        epi_to_T1_workflow.connect(input_node, 'freesurfer_subject_dir', bbregister_N, 'subjects_dir')

        epi_to_T1_workflow.connect(bbregister_N, 'out_fsl_file', output_node, 'out_matrix_file')
        epi_to_T1_workflow.connect(bbregister_N, 'out_reg_file', output_node, 'EPI_T1_register_file')

        # the final invert node
        invert_N = pe.Node(fsl.ConvertXFM(invert_xfm = True), name = 'invert_N')
        epi_to_T1_workflow.connect(bbregister_N, 'out_fsl_file', invert_N, 'in_file')
        epi_to_T1_workflow.connect(invert_N, 'out_file', output_node, 'T1_EPI_matrix_file')


    else: # do flirt
        flirt_N = pe.Node(fsl.FLIRT(cost_func='bbr', output_type = 'NIFTI_GZ', dof = 12, interp = 'sinc'),
                          name = 'flirt_N')
        epi_to_T1_workflow.connect(input_node, 'EPI_space_file', flirt_N, 'in_file')
        epi_to_T1_workflow.connect(input_node, 'T1_file', flirt_N, 'reference')
        epi_to_T1_workflow.connect(input_node, 'EPI_space_file', flirt_N, 'in_file')

        epi_to_T1_workflow.connect(flirt_N, 'out_matrix_file', output_node, 'EPI_T1_matrix_file')

        # the final invert node
        invert_N = pe.Node(fsl.ConvertXFM(invert_xfm = True), name = 'invert_N')
        epi_to_T1_workflow.connect(flirt_N, 'out_matrix_file', invert_N, 'in_file')
        epi_to_T1_workflow.connect(invert_N, 'out_file', output_node, 'T1_EPI_matrix_file')


    return epi_to_T1_workflow

if __name__ == '__main__':

    pass