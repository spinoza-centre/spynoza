import nipype.pipeline as pe
from nipype.interfaces import fsl
from nipype.interfaces import freesurfer
from nipype.interfaces import ants
from nipype.interfaces.utility import Function, IdentityInterface
from ...utils import pick_last
import pkg_resources


def create_epi_to_T1_workflow(name='epi_to_T1', 
                              package='freesurfer',
                              init_reg_file=None,
                              do_BET=False,
                              do_FAST=True,
                              parameter_file='linear_precise.json',
                              num_threads_ants=4,
                              apply_transform=False):
    """Registers session's EPI space to subject's T1 space
    uses either FLIRT or, when a FS segmentation is present, BBRegister
    Requires fsl and freesurfer tools

    Parameters
    ----------
    name : string
        name of workflow
    use_FS : bool
        whether to use freesurfer's segmentation and BBRegister
    init_reg_file : file
        (optional) provide a freesurfer "LTA"-image to initalize registration with
    do_BET : bool
        whether to use FSL's BET to brain-extract the T1-weighted image
    do_FAST : bool
        whether to apply FSL's FAST (segmentation into CSF/GM/WM) to T1-weighted image
    parameter_file : string
        file in spynoza/spynoza/data/ants_json to initialize ANTS with
    apply_transform : bool
        whether to apply the computed transofmration matrix on the input (e.g., for
        checking purposes)
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
          inputspec.wm_seg_file : nifti-file with white matter segmentation
          Outputs::
           outputspec.EPI_T1_register_file : BBRegister registration file that maps EPI space to T1
           outputspec.EPI_T1_matrix_file : FLIRT registration file that maps EPI space to T1
           outputspec.T1_EPI_matrix_file : FLIRT registration file that maps T1 space to EPI
    """

    input_node = pe.Node(IdentityInterface(
        fields=['EPI_space_file', 'freesurfer_subject_ID',
                'freesurfer_subject_dir', 'T1_file', 'wm_seg_file']), name='inputspec')

    # Idea: also output FAST outputs for later use?
    fields = ['EPI_T1_matrix_file',
              'T1_EPI_matrix_file',
              'EPI_T1_register_file']

    if apply_transform:
        fields.append('transformed_EPI_space_file')

    output_node = pe.Node(IdentityInterface(fields=fields),
                          name='outputspec')

    epi_to_T1_workflow = pe.Workflow(name=name)



    if package == 'freesurfer': # do BBRegister
        if init_reg_file is None:
            bbregister_N = pe.Node(freesurfer.BBRegister(init = 'fsl', contrast_type = 't2', out_fsl_file = True ),
                               name = 'bbregister_N')
        else:
            bbregister_N = pe.Node(freesurfer.BBRegister(init_reg_file=init_reg_file, contrast_type = 't2', out_fsl_file = True ),
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

    elif package == 'fsl':  # do FAST + FLIRT

        if do_BET:
            bet = pe.Node(fsl.BET(), name='bet')
            epi_to_T1_workflow.connect(input_node, 'T1_file', bet, 'in_file')

        flirt_e2t = pe.Node(fsl.FLIRT(cost_func='bbr', output_type='NIFTI_GZ',
                                    dof=12, interp='sinc'),
                          name ='flirt_e2t')


        if init_reg_file is not None:
            if init_reg_file.endswith('lta'):
                convert_init_reg = pe.Node(freesurfer.utils.LTAConvert(in_lta=init_reg_file,
                                                                  out_fsl=True), 
                                           name='convert_init_reg_to_fsl')
                epi_to_T1_workflow.connect(input_node, 'EPI_space_file', convert_init_reg, 'source_file')
                epi_to_T1_workflow.connect(input_node, 'T1_file', convert_init_reg, 'target_file')
                epi_to_T1_workflow.connect(convert_init_reg, 'out_fsl', flirt_e2t, 'in_matrix_file')
            else:
                flirt_e2t.inputs.in_matrix_file = init_reg_file


        epi_to_T1_workflow.connect(input_node, 'EPI_space_file', flirt_e2t, 'in_file')

        if do_FAST:
            fast = pe.Node(fsl.FAST(no_pve=True, img_type=1, segments=True),
                           name='fast')

            if do_BET:
                epi_to_T1_workflow.connect(bet, 'out_file', fast, 'in_files')
            else:
                epi_to_T1_workflow.connect(input_node, 'T1_file', fast, 'in_files')

            epi_to_T1_workflow.connect(fast, ('tissue_class_files', pick_last), flirt_e2t, 'wm_seg')

        elif not do_FAST and flirt_e2t.inputs.cost_func == 'bbr':
            epi_to_T1_workflow.connect(input_node, 'wm_seg_file', flirt_e2t, 'wm_seg')

        if do_BET:
            epi_to_T1_workflow.connect(bet, 'out_file', flirt_e2t, 'reference')
        else:
            epi_to_T1_workflow.connect(input_node, 'T1_file', flirt_e2t, 'reference')

        epi_to_T1_workflow.connect(flirt_e2t, 'out_matrix_file', output_node, 'EPI_T1_matrix_file')

        # the final invert node
        invert_EPI_N = pe.Node(fsl.ConvertXFM(invert_xfm = True), name='invert_EPI_N')
        epi_to_T1_workflow.connect(flirt_e2t, 'out_matrix_file', invert_EPI_N, 'in_file')
        epi_to_T1_workflow.connect(invert_EPI_N, 'out_file', output_node, 'T1_EPI_matrix_file')

        if apply_transform:
            applier = pe.Node(fsl.ApplyXFM(), name='applier')
            epi_to_T1_workflow.connect(flirt_e2t, 'out_matrix_file', applier, 'in_matrix_file')
            epi_to_T1_workflow.connect(input_node, 'EPI_space_file', applier, 'in_file')
            epi_to_T1_workflow.connect(input_node, 'T1_file', applier, 'reference')
            epi_to_T1_workflow.connect(applier, 'out_file', output_node, 'transformed_EPI_space_file')
    
    elif package == 'ants':

        if do_BET:
            bet = pe.Node(fsl.BET(), name='bet')
            epi_to_T1_workflow.connect(input_node, 'T1_file', bet, 'in_file')

        
        bold_registration_json = pkg_resources.resource_filename('spynoza.data.ants_json', parameter_file)
        ants_registration = pe.Node(ants.Registration(from_file=bold_registration_json,
                                                      num_threads=4,
                                                      output_warped_image=apply_transform), 
                                    name='ants_registration')

        if init_reg_file is not None:
            if init_reg_file.endswith('lta'):
                convert_to_ants = pe.Node(freesurfer.utils.LTAConvert(in_lta=init_reg_file,
                                                                     out_itk=True), name='convert_to_itk')

                epi_to_T1_workflow.connect(input_node, 'EPI_space_file', convert_to_ants, 'source_file')
                epi_to_T1_workflow.connect(input_node, 'T1_file', convert_to_ants, 'target_file')
                
                epi_to_T1_workflow.connect(convert_to_ants, 'out_itk', ants_registration, 'initial_moving_transform')
            
            else:
                reg.inputs.initial_moving_transform = init_reg_file



        epi_to_T1_workflow.connect(input_node, 'EPI_space_file', ants_registration, 'moving_image')

        if do_BET:
            epi_to_T1_workflow.connect(bet, 'out_file', ants_registration, 'fixed_image')
        else:
            epi_to_T1_workflow.connect(input_node, 'T1_file', ants_registration, 'fixed_image')

        epi_to_T1_workflow.connect(ants_registration, 'forward_transforms', output_node, 'EPI_T1_matrix_file')

        # the final invert node
        epi_to_T1_workflow.connect(ants_registration, 'reverse_transforms', output_node, 'T1_EPI_matrix_file')

        if apply_transform:
            epi_to_T1_workflow.connect(ants_registration, 'warped_image', output_node, 'transformed_EPI_space_file')

    return epi_to_T1_workflow
