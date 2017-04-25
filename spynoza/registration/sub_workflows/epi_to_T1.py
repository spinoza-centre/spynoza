import nipype.pipeline as pe
from nipype.interfaces import fsl
from nipype.interfaces import freesurfer
from nipype.interfaces.utility import Function, IdentityInterface
from ...utils import pick_last


def create_epi_to_T1_workflow(name='epi_to_T1', use_FS=True,
                              do_FAST=True):
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

    input_node = pe.Node(IdentityInterface(
        fields=['EPI_space_file', 'output_directory', 'freesurfer_subject_ID',
                'freesurfer_subject_dir', 'T1_file']), name='inputspec')

    # Idea: also output FAST outputs for later use?
    output_node = pe.Node(IdentityInterface(fields=('EPI_T1_matrix_file',
                                                    'T1_EPI_matrix_file',
                                                    'EPI_T1_register_file')),
                          name='outputspec')

    epi_to_T1_workflow = pe.Workflow(name=name)

    if use_FS: # do BBRegister
        bbregister_N = pe.Node(freesurfer.BBRegister(init = 'fsl', contrast_type = 't2', out_fsl_file = True ),
                               name = 'bbregister_N')

        epi_to_T1_workflow.connect(input_node, 'EPI_space_file', bbregister_N, 'source_file')
        epi_to_T1_workflow.connect(input_node, 'freesurfer_subject_ID', bbregister_N, 'subject_id')
        epi_to_T1_workflow.connect(input_node, 'freesurfer_subject_dir', bbregister_N, 'subjects_dir')

        epi_to_T1_workflow.connect(bbregister_N, 'out_fsl_file', output_node, 'EPI_T1_matrix_file')
        epi_to_T1_workflow.connect(bbregister_N, 'out_reg_file', output_node, 'EPI_T1_register_file')

        # the final invert node
        invert_EPI_N = pe.Node(fsl.ConvertXFM(invert_xfm = True), name = 'invert_EPI_N')
        epi_to_T1_workflow.connect(bbregister_N, 'out_fsl_file', invert_EPI_N, 'in_file')
        epi_to_T1_workflow.connect(invert_EPI_N, 'out_file', output_node, 'T1_EPI_matrix_file')

    else:  # do FAST + FLIRT

        flirt_e2t = pe.Node(fsl.FLIRT(cost_func='bbr', output_type='NIFTI_GZ',
                                    dof=12, interp='sinc'),
                          name ='flirt_e2t')

        epi_to_T1_workflow.connect(input_node, 'EPI_space_file', flirt_e2t, 'in_file')

        if do_FAST:
            fast = pe.Node(fsl.FAST(no_pve=True, img_type=1, segments=True),
                           name='fast')

            epi_to_T1_workflow.connect(input_node, 'T1_file', fast, 'in_files')
            epi_to_T1_workflow.connect(fast, ('tissue_class_files', pick_last), flirt_e2t, 'wm_seg')
        elif not do_FAST and flirt_e2t.inputs.cost_func == 'bbr':
            print('You indicated not wanting to do FAST, but still wanting to do a'
                  ' BBR epi-to-T1 registration. That is probably not going to work ...')

        epi_to_T1_workflow.connect(input_node, 'T1_file', flirt_e2t, 'reference')
        epi_to_T1_workflow.connect(flirt_e2t, 'out_matrix_file', output_node, 'EPI_T1_matrix_file')

        # the final invert node
        invert_EPI_N = pe.Node(fsl.ConvertXFM(invert_xfm = True), name='invert_EPI_N')
        epi_to_T1_workflow.connect(flirt_e2t, 'out_matrix_file', invert_EPI_N, 'in_file')
        epi_to_T1_workflow.connect(invert_EPI_N, 'out_file', output_node, 'T1_EPI_matrix_file')

    return epi_to_T1_workflow
