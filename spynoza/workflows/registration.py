import os.path as op
import json
import nipype.pipeline as pe
from sub_workflows import *


def create_registration_workflow(name = 'reg', session_info ):
	"""uses sub-workflows to perform different registration steps.
    Requires fsl and freesurfer tools
    Parameters
    ----------
    name : string
        name of workflow
    session_info : dict 
        contains session information needed for workflow, such as
        whether to use FreeSurfer or FLIRT etc.
    Example
    -------
    >>> registration_workflow = create_registration_workflow('registration_workflow', session_info = {'use_FS':True})
    >>> registration_workflow.inputs.inputspec.output_directory = '/data/project/raw/BIDS/sj_1/'
    >>> registration_workflow.inputs.inputspec.EPI_space_file = 'example_Func.nii.gz'
    >>> registration_workflow.inputs.inputspec.T1_file = 'T1.nii.gz' # optional if using freesurfer
    >>> registration_workflow.inputs.inputspec.freesurfer_subject_ID = 'sub_01'
    >>> registration_workflow.inputs.inputspec.freesurfer_subject_dir = '$SUBJECTS_DIR'
    >>> registration_workflow.inputs.inputspec.reference_file = '/usr/local/fsl/data/standard/standard152_T1_2mm_brain.nii.gz'
    >>> registration_workflow.inputs.inputspec.freesurfer_subject_dir = '$SUBJECTS_DIR'
    >>> registration_workflow.inputs.inputspec.freesurfer_subject_dir = '$SUBJECTS_DIR'
 
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
        fields=['EPI_space_file', 'output_directory', 'freesurfer_subject_ID', 'freesurfer_subject_dir', 'T1_file',
        	'standard_file'
        ]), name='inputspec')

    ### Workflow to be returned
    registration_workflow = pe.Workflow(name='registration_workflow')

    ### sub-workflows
    epi_2_T1 = create_epi_to_T1_workflow( name = 'epi', use_FS = session_info['use_FS'] )
    T1_to_standard = create_T1_to_standard_workflow( name = 'T1_to_standard' )
    concat_2_feat = create_concat_2_feat_workflow( name = 'concat_2_feat' )

    output_node = pe.Node(IdentityInterface(fields=('EPI_T1_matrix_file',  
                                                    'T1_EPI_matrix_file', 
                                                    'EPI_T1_register_file',
                                                    'T1_standard_matrix_file', 
                                                    'standard_T1_matrix_file', 
                                                    'EPI_T1_matrix_file', 
                                                    'T1_EPI_matrix_file', 
                                                    'T1_file',
                                                    'standard_file',
                                                    'EPI_space_file'
        )), name='outputspec')

    ########################################################################################
    # EPI to T1
    ########################################################################################

    registration_workflow.connect([(inputnode, epi_2_T1, [
                                            ('EPI_space_file','inputspec.EPI_space_file'),
                                            ('output_directory', 'inputspec.output_directory'),
                                            ('freesurfer_subject_ID', 'inputspec.freesurfer_subject_ID'),
                                            ('freesurfer_subject_dir', 'inputspec.freesurfer_subject_dir'),
                                            ('T1_file', 'inputspec.T1_file')
                                            ])])

    ########################################################################################
    # T1 to standard
    ########################################################################################

    registration_workflow.connect([(inputnode, T1_to_standard, [
                                            ('output_directory', 'inputspec.output_directory'),
                                            ('freesurfer_subject_ID', 'inputspec.freesurfer_subject_ID'),
                                            ('freesurfer_subject_dir', 'inputspec.freesurfer_subject_dir'),
                                            ('T1_file', 'inputspec.T1_file'),
                                            ('reference_file', 'inputspec.reference_file')
                                            ])])

    ########################################################################################
    # concatenation of all matrices
    ########################################################################################

    # first the inputs from the input node
    registration_workflow.connect([(inputnode, concat_2_feat, [
                                            ('output_directory', 'inputspec.output_directory'),
                                            ('freesurfer_subject_ID', 'inputspec.freesurfer_subject_ID'),
                                            ('freesurfer_subject_dir', 'inputspec.freesurfer_subject_dir'),
                                            ('EPI_space_file','inputspec.EPI_space_file'),
                                            ('T1_file', 'inputspec.T1_file'),
                                            ('standard_file', 'inputspec.standard_file'),
                                            ])])

    # then, the inputs from the previous sub-workflows
    registration_workflow.connect([(epi_2_T1, concat_2_feat, [
                                            ('outputspec.EPI_T1_matrix_file', 'inputspec.EPI_T1_matrix_file'),
                                            ('outputspec.T1_EPI_matrix_file', 'inputspec.T1_EPI_matrix_file')
                                            ])])

    registration_workflow.connect([(T1_to_standard, concat_2_feat, [
                                            ('outputspec.T1_standard_matrix_file', 'inputspec.T1_standard_matrix_file'),
                                            ('outputspec.standard_T1_matrix_file', 'inputspec.standard_T1_matrix_file')


    # outputs via datasink
    datasink = pe.Node(nio.DataSink(), name='sinker')

    # first link the workflow's output_directory into the datasink.
    registration_workflow.connect(input_node, 'output_directory', datasink, 'base_directory')

    # start work on the creation of a registration folder.
    # put the used nifti files in the reg/feat directory.
    registration_workflow.connect(input_node, 'EPI_space_file', datasink, 'reg.feat.example_func.@nii.@gz')
    registration_workflow.connect(input_node, 'T1_file', datasink, 'reg.feat.highres.@nii.@gz')
    registration_workflow.connect(input_node, 'standard_file', datasink, 'reg.feat.standard_file.@nii.@gz')

    # put the created .dat file in the reg directory.
    registration_workflow.connect(epi_to_T1_workflow, 'outputspec.EPI_T1_register_file', datasink, 'reg.register.@dat')
    # put the created .mat files in the reg/feat directory.
    registration_workflow.connect(epi_to_T1_workflow, 'outputspec.EPI_T1_matrix_file', datasink, 'reg.feat.example_func2highres.@mat')
    registration_workflow.connect(epi_to_T1_workflow, 'outputspec.T1_EPI_matrix_file', datasink, 'reg.feat.highres2example_func.@mat')

    registration_workflow.connect(T1_to_standard_workflow, 'outputspec.T1_standard_matrix_file', datasink, 'reg.feat.highres2standard.@mat')
    registration_workflow.connect(T1_to_standard_workflow, 'outputspec.standard_T1_matrix_file', datasink, 'reg.feat.standard2highres.@mat')

    registration_workflow.connect(concat_2_feat_workflow, 'outputspec.EPI_standard_matrix_file', datasink, 'reg.feat.example_func2standard.@mat')
    registration_workflow.connect(concat_2_feat_workflow, 'outputspec.standard_EPI_matrix_file', datasink, 'reg.feat.standard2example_func.@mat')

