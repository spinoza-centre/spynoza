import os.path as op
import json
import nipype.pipeline as pe
from nipype.interfaces.utility import Function, IdentityInterface
import nipype.interfaces.io as nio
from .sub_workflows import *


def create_registration_workflow(session_info, name = 'reg'):
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
    >>> registration_workflow = create_registration_workflow(name = 'registration_workflow', session_info = {'use_FS':True})
    >>> registration_workflow.inputs.inputspec.output_directory = '/data/project/raw/BIDS/sj_1/'
    >>> registration_workflow.inputs.inputspec.EPI_space_file = 'example_func.nii.gz'
    >>> registration_workflow.inputs.inputspec.T1_file = 'T1.nii.gz' # if using freesurfer, this file will be created instead of used.
    >>> registration_workflow.inputs.inputspec.freesurfer_subject_ID = 'sub_01'
    >>> registration_workflow.inputs.inputspec.freesurfer_subject_dir = '$SUBJECTS_DIR'
    >>> registration_workflow.inputs.inputspec.reference_file = '/usr/local/fsl/data/standard/standard152_T1_2mm_brain.nii.gz'
 
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
    import nipype.pipeline as pe
    from nipype.interfaces.utility import Function, IdentityInterface, Merge
    import nipype.interfaces.io as nio
    import nipype.interfaces.utility as niu

    ### NODES
    input_node = pe.Node(IdentityInterface(fields=['EPI_space_file',
                                                'output_directory', 
                                                'freesurfer_subject_ID', 
                                                'freesurfer_subject_dir', 
                                                'T1_file',
                                                'standard_file']), name='inputspec')

    ### Workflow to be returned
    registration_workflow = pe.Workflow(name=name)

    ### sub-workflows
    epi_2_T1 = create_epi_to_T1_workflow( name = 'epi', use_FS = session_info['use_FS'] )
    T1_to_standard = create_T1_to_standard_workflow( name = 'T1_to_standard', use_FS = session_info['use_FS'], do_fnirt =  session_info['do_fnirt'])
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

    registration_workflow.connect([(input_node, epi_2_T1, [
                                            ('EPI_space_file','inputspec.EPI_space_file'),
                                            ('output_directory', 'inputspec.output_directory'),
                                            ('freesurfer_subject_ID', 'inputspec.freesurfer_subject_ID'),
                                            ('freesurfer_subject_dir', 'inputspec.freesurfer_subject_dir'),
                                            ('T1_file', 'inputspec.T1_file')
                                            ])])

    ########################################################################################
    # T1 to standard
    ########################################################################################

    registration_workflow.connect([(input_node, T1_to_standard, [
                                            ('freesurfer_subject_ID', 'inputspec.freesurfer_subject_ID'),
                                            ('freesurfer_subject_dir', 'inputspec.freesurfer_subject_dir'),
                                            ('T1_file', 'inputspec.T1_file'),
                                            ('standard_file', 'inputspec.standard_file')
                                            ])])

    ########################################################################################
    # concatenation of all matrices
    ########################################################################################

    # then, the inputs from the previous sub-workflows
    registration_workflow.connect([(epi_2_T1, concat_2_feat, [
                                            ('outputspec.EPI_T1_matrix_file', 'inputspec.EPI_T1_matrix_file'),
                                            ])])

    registration_workflow.connect([(T1_to_standard, concat_2_feat, [
                                            ('outputspec.T1_standard_matrix_file', 'inputspec.T1_standard_matrix_file'),
                                            ])])

    ########################################################################################
    # Rename nodes, for the datasink
    ########################################################################################
    rename_register = pe.Node(niu.Rename(format_string='register.dat', keep_ext=False), name='rename_register')
    registration_workflow.connect(epi_2_T1, 'outputspec.EPI_T1_register_file', rename_register, 'in_file')

    rename_example_func = pe.Node(niu.Rename(format_string='example_func', keep_ext=True), name='rename_example_func')
    registration_workflow.connect(input_node, 'EPI_space_file', rename_example_func, 'in_file')

    rename_highres = pe.Node(niu.Rename(format_string='highres', keep_ext=True), name='rename_highres')
    registration_workflow.connect(T1_to_standard, 'outputspec.T1_file', rename_highres, 'in_file')

    rename_standard = pe.Node(niu.Rename(format_string='standard', keep_ext=True), name='rename_standard')
    registration_workflow.connect(input_node, 'standard_file', rename_standard, 'in_file')

    rename_example_func2standard = pe.Node(niu.Rename(format_string='example_func2standard.mat', keep_ext=False), name='rename_example_func2standard')
    registration_workflow.connect(concat_2_feat, 'outputspec.EPI_standard_matrix_file', rename_example_func2standard, 'in_file')

    rename_example_func2highres = pe.Node(niu.Rename(format_string='example_func2highres.mat', keep_ext=False), name='rename_example_func2highres')
    registration_workflow.connect(epi_2_T1, 'outputspec.EPI_T1_matrix_file', rename_example_func2highres, 'in_file')

    rename_highres2standard = pe.Node(niu.Rename(format_string='highres2standard.mat', keep_ext=False), name='rename_highres2standard')
    registration_workflow.connect(T1_to_standard, 'outputspec.T1_standard_matrix_file', rename_highres2standard, 'in_file')

    rename_standard2example_func = pe.Node(niu.Rename(format_string='standard2example_func.mat', keep_ext=False), name='rename_standard2example_func')
    registration_workflow.connect(concat_2_feat, 'outputspec.standard_EPI_matrix_file', rename_standard2example_func, 'in_file')

    rename_highres2example_func = pe.Node(niu.Rename(format_string='highres2example_func.mat', keep_ext=False), name='rename_highres2example_func')
    registration_workflow.connect(epi_2_T1, 'outputspec.T1_EPI_matrix_file', rename_highres2example_func, 'in_file')

    rename_standard2highres = pe.Node(niu.Rename(format_string='standard2highres.mat', keep_ext=False), name='rename_standard2highres')
    registration_workflow.connect(T1_to_standard, 'outputspec.standard_T1_matrix_file', rename_standard2highres, 'in_file')

    merge_for_reg_N = pe.Node(Merge(10), infields =
                        ['register','example_func','highres','standard',
                        'example_func2standard', 'example_func2highres', 'highres2standard',
                        'standard2example_func', 'highres2example_func', 'standard2highres'
                        ], name='merge_for_reg_N')

    registration_workflow.connect(rename_register, 'out_file', merge_for_reg_N, 'register')
    registration_workflow.connect(rename_example_func, 'out_file', merge_for_reg_N, 'example_func')
    registration_workflow.connect(rename_highres, 'out_file', merge_for_reg_N, 'highres')
    registration_workflow.connect(rename_standard, 'out_file', merge_for_reg_N, 'standard')
    registration_workflow.connect(rename_example_func2highres, 'out_file', merge_for_reg_N, 'example_func2highres')
    registration_workflow.connect(rename_highres2example_func, 'out_file', merge_for_reg_N, 'highres2example_func')
    registration_workflow.connect(rename_highres2standard, 'out_file', merge_for_reg_N, 'highres2standard')
    registration_workflow.connect(rename_standard2highres, 'out_file', merge_for_reg_N, 'standard2highres')
    registration_workflow.connect(rename_example_func2standard, 'out_file', merge_for_reg_N, 'example_func2standard')
    registration_workflow.connect(rename_standard2example_func, 'out_file', merge_for_reg_N, 'standard2example_func')
   
    # outputs via datasink
    datasink = pe.Node(nio.DataSink(infields=['reg']), name='sinker')
    registration_workflow.connect(input_node, 'output_directory', datasink, 'base_directory')
    # put the nifti and mat files, renamed above, in the reg/feat directory.
    # don't yet know what's wrong with this merge to datasink
    # registration_workflow.connect(merge_for_reg_N, 'out', datasink, 'reg')

    registration_workflow.connect(epi_2_T1, 'outputspec.EPI_T1_register_file', datasink, 'reg.register.@dat')
    registration_workflow.connect(input_node, 'EPI_space_file', datasink, 'reg.example_func')
    registration_workflow.connect(input_node, 'standard_file', datasink, 'reg.standard')
    registration_workflow.connect(T1_to_standard, 'outputspec.T1_file', datasink, 'reg.highres')

    registration_workflow.connect(epi_2_T1, 'outputspec.EPI_T1_matrix_file', datasink, 'reg.example_func2highres.@mat')
    registration_workflow.connect(epi_2_T1, 'outputspec.T1_EPI_matrix_file', datasink, 'reg.highres2example_func.@mat')
    registration_workflow.connect(T1_to_standard, 'outputspec.T1_standard_matrix_file', datasink, 'reg.highres2standard.@mat')
    registration_workflow.connect(T1_to_standard, 'outputspec.standard_T1_matrix_file', datasink, 'reg.standard2highres.@mat')
    registration_workflow.connect(concat_2_feat, 'outputspec.standard_EPI_matrix_file', datasink, 'reg.standard2example_func.@mat')
    registration_workflow.connect(concat_2_feat, 'outputspec.EPI_standard_matrix_file', datasink, 'reg.example_func2standard.@mat')


    return registration_workflow
