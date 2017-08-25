from __future__ import absolute_import
import nipype.pipeline as pe
from nipype.interfaces.utility import IdentityInterface
from nipype.interfaces.utility import Rename
from nipype.interfaces.io import DataSink

from .sub_workflows import (create_concat_2_feat_workflow,
                            create_epi_to_T1_workflow,
                            create_T1_to_standard_workflow)


def create_registration_workflow(analysis_info, name='reg'):
    """uses sub-workflows to perform different registration steps.
    Requires fsl and freesurfer tools
    Parameters
    ----------
    name : string
        name of workflow
    analysis_info : dict
        contains session information needed for workflow, such as
        whether to use FreeSurfer or FLIRT etc.
    Example
    -------
    >>> registration_workflow = create_registration_workflow(name = 'registration_workflow', analysis_info = {'use_FS':True})
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

    ### NODES
    input_node = pe.Node(IdentityInterface(fields=['EPI_space_file',
                                                   'output_directory',
                                                   'freesurfer_subject_ID',
                                                   'freesurfer_subject_dir',
                                                   'T1_file',
                                                   'standard_file',
                                                   'sub_id']), name='inputspec')

    ### Workflow to be returned
    registration_workflow = pe.Workflow(name=name)

    ### sub-workflows
    epi_2_T1 = create_epi_to_T1_workflow(name='epi',
                                         use_FS=analysis_info['use_FS'],
                                         do_BET=analysis_info['do_BET'],
                                         do_FAST=analysis_info['do_FAST'])
    T1_to_standard = create_T1_to_standard_workflow(name='T1_to_standard',
                                                    use_FS=analysis_info[
                                                        'use_FS'],
                                                    do_fnirt=analysis_info[
                                                        'do_fnirt'],
                                                    use_AFNI_ss=analysis_info['use_AFNI_ss'])
    concat_2_feat = create_concat_2_feat_workflow(name='concat_2_feat')

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

    ###########################################################################
    # EPI to T1
    ###########################################################################

    registration_workflow.connect([(input_node, epi_2_T1, [
        ('EPI_space_file', 'inputspec.EPI_space_file'),
        ('output_directory', 'inputspec.output_directory'),
        ('freesurfer_subject_ID', 'inputspec.freesurfer_subject_ID'),
        ('freesurfer_subject_dir', 'inputspec.freesurfer_subject_dir'),
        ('T1_file', 'inputspec.T1_file')
    ])])

    ###########################################################################
    # T1 to standard
    ###########################################################################

    registration_workflow.connect([(input_node, T1_to_standard, [
        ('freesurfer_subject_ID', 'inputspec.freesurfer_subject_ID'),
        ('freesurfer_subject_dir', 'inputspec.freesurfer_subject_dir'),
        ('T1_file', 'inputspec.T1_file'),
        ('standard_file', 'inputspec.standard_file')
    ])])

    ###########################################################################
    # concatenation of all matrices
    ###########################################################################

    # then, the inputs from the previous sub-workflows
    registration_workflow.connect([(epi_2_T1, concat_2_feat, [
        ('outputspec.EPI_T1_matrix_file', 'inputspec.EPI_T1_matrix_file'),
    ])])

    registration_workflow.connect([(T1_to_standard, concat_2_feat, [
        ('outputspec.T1_standard_matrix_file',
         'inputspec.T1_standard_matrix_file'),
    ])])

    ###########################################################################
    # Rename nodes, for the datasink
    ###########################################################################

    if analysis_info['use_FS']:
        rename_register = pe.Node(
            Rename(format_string='register.dat', keep_ext=False),
            name='rename_register')

        registration_workflow.connect(epi_2_T1,
                                      'outputspec.EPI_T1_register_file',
                                      rename_register, 'in_file')

    rename_example_func = pe.Node(
        Rename(format_string='example_func', keep_ext=True),
        name='rename_example_func')

    registration_workflow.connect(input_node, 'EPI_space_file',
                                  rename_example_func, 'in_file')

    rename_highres = pe.Node(Rename(format_string='highres', keep_ext=True),
                             name='rename_highres')
    registration_workflow.connect(T1_to_standard, 'outputspec.T1_file',
                                  rename_highres, 'in_file')

    rename_standard = pe.Node(
        Rename(format_string='standard', keep_ext=True),
        name='rename_standard')

    registration_workflow.connect(input_node, 'standard_file', rename_standard,
                                  'in_file')

    rename_example_func2standard = pe.Node(
        Rename(format_string='example_func2standard.mat', keep_ext=False),
        name='rename_example_func2standard')

    registration_workflow.connect(concat_2_feat,
                                  'outputspec.EPI_standard_matrix_file',
                                  rename_example_func2standard, 'in_file')

    rename_example_func2highres = pe.Node(
        Rename(format_string='example_func2highres.mat', keep_ext=False),
        name='rename_example_func2highres')

    registration_workflow.connect(epi_2_T1, 'outputspec.EPI_T1_matrix_file',
                                  rename_example_func2highres, 'in_file')

    rename_highres2standard = pe.Node(
        Rename(format_string='highres2standard.mat', keep_ext=False),
        name='rename_highres2standard')
    registration_workflow.connect(T1_to_standard,
                                  'outputspec.T1_standard_matrix_file',
                                  rename_highres2standard, 'in_file')

    rename_standard2example_func = pe.Node(
        Rename(format_string='standard2example_func.mat', keep_ext=False),
        name='rename_standard2example_func')

    registration_workflow.connect(concat_2_feat,
                                  'outputspec.standard_EPI_matrix_file',
                                  rename_standard2example_func, 'in_file')

    rename_highres2example_func = pe.Node(
        Rename(format_string='highres2example_func.mat', keep_ext=False),
        name='rename_highres2example_func')

    registration_workflow.connect(epi_2_T1, 'outputspec.T1_EPI_matrix_file',
                                  rename_highres2example_func, 'in_file')

    rename_standard2highres = pe.Node(
        Rename(format_string='standard2highres.mat', keep_ext=False),
        name='rename_standard2highres')
    registration_workflow.connect(T1_to_standard,
                                  'outputspec.standard_T1_matrix_file',
                                  rename_standard2highres, 'in_file')

    # outputs via datasink
    datasink = pe.Node(DataSink(infields=['reg']), name='sinker')
    datasink.inputs.parameterization = False
    registration_workflow.connect(input_node, 'output_directory', datasink,
                                  'base_directory')
    registration_workflow.connect(input_node, 'sub_id', datasink, 'container')

    # NEW SETUP WITH RENAME (WITHOUT MERGER)
    if analysis_info['use_FS']:
        registration_workflow.connect(rename_register, 'out_file', datasink,
                                      'reg.@dat')

    registration_workflow.connect(rename_example_func, 'out_file', datasink,
                                  'reg.@example_func')
    registration_workflow.connect(rename_standard, 'out_file', datasink,
                                  'reg.@standard')
    registration_workflow.connect(rename_highres, 'out_file', datasink,
                                  'reg.@highres')
    registration_workflow.connect(rename_example_func2highres, 'out_file',
                                  datasink, 'reg.@example_func2highres')
    registration_workflow.connect(rename_highres2example_func, 'out_file',
                                  datasink, 'reg.@highres2example_func')
    registration_workflow.connect(rename_highres2standard, 'out_file', datasink,
                                  'reg.@highres2standard')
    registration_workflow.connect(rename_standard2highres, 'out_file', datasink,
                                  'reg.@standard2highres')
    registration_workflow.connect(rename_standard2example_func, 'out_file',
                                  datasink, 'reg.@standard2example_func')
    registration_workflow.connect(rename_example_func2standard, 'out_file',
                                  datasink, 'reg.@example_func2standard')

    registration_workflow.connect(rename_highres, 'out_file', output_node,
                                  'T1_file')

    # put the nifti and mat files, renamed above, in the reg/feat directory.
    # don't yet know what's wrong with this merge to datasink
    # registration_workflow.connect(merge_for_reg_N, 'out', datasink, 'reg')

    return registration_workflow
