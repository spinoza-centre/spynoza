import os.path as op
import json
import nipype.pipeline as pe
import nipype.interfaces.fsl as fsl
import nipype.interfaces.utility as util
import nipype.interfaces.io as nio
from nipype.interfaces.utility import Function, IdentityInterface
from .sub_workflows import *
import nipype.interfaces.utility as niu

def EPI_file_selector(which_file, in_files):
    """Selects which EPI file will be the standard EPI space.
    Choices are: 'middle', 'last', 'first', or any integer in the list
    """
    import math

    if which_file == 'middle':
        return in_files[int(math.floor(len(in_files)/2))]
    elif which_file == 'first':
        return in_files[0]
    elif which_file == 'last':
        return in_files[-1]
    elif type(which_file) == int:
        return in_files[which_file]

def create_motion_correction_workflow(name = 'moco'):
    """uses sub-workflows to perform different registration steps.
    Requires fsl and freesurfer tools
    Parameters
    ----------
    name : string
        name of workflow
    
    Example
    -------
    >>> motion_correction_workflow = create_motion_correction_workflow('motion_correction_workflow')
    >>> motion_correction_workflow.inputs.inputspec.output_directory = '/data/project/raw/BIDS/sj_1/'
    >>> motion_correction_workflow.inputs.inputspec.in_files = ['sub-001.nii.gz','sub-002.nii.gz']
    >>> motion_correction_workflow.inputs.inputspec.which_file_is_EPI_space = 'middle'
 
    Inputs::
          inputspec.output_directory : directory in which to sink the result files
          inputspec.in_files : list of functional files
          inputspec.which_file_is_EPI_space : determines which file is the 'standard EPI space'
    Outputs::
           outputspec.EPI_space_file : standard EPI space file, one timepoint
           outputspec.motion_corrected_files : motion corrected files
           outputspec.motion_correction_plots : motion correction plots
           outputspec.motion_correction_parameters : motion correction parameters
    """
    import os.path as op
    import nipype.pipeline as pe
    import nipype.interfaces.fsl as fsl
    import nipype.interfaces.utility as util
    import nipype.interfaces.io as nio
    from nipype.interfaces.utility import Function, IdentityInterface
    import nipype.interfaces.utility as niu
    ### NODES
    input_node = pe.Node(IdentityInterface(fields=['in_files', 'output_directory', 'which_file_is_EPI_space']), name='inputspec')
    output_node = pe.Node(IdentityInterface(fields=([
                'motion_corrected_files', 
                'EPI_space_file', 
                'motion_correction_plots', 
                'motion_correction_parameters'])), name='outputspec')

    EPI_file_selector_node = pe.Node(Function(input_names=['which_file', 'in_files'], output_names='raw_EPI_space_file',
                                       function=EPI_file_selector), name='EPI_file_selector_node')

    motion_correct_EPI_space = pe.Node(interface=fsl.MCFLIRT(
                    save_mats = True, 
                    save_plots = True, 
                    cost = 'normmi', 
                    interpolation = 'sinc'
                    ), name='realign_space')

    mean_bold = pe.Node(interface=fsl.maths.MeanImage(dimension='T'), name='mean_space')

    motion_correct_all = pe.MapNode(interface=fsl.MCFLIRT(
                       save_mats = True, 
                    save_plots = True, 
                    cost = 'normmi', 
                    interpolation = 'sinc',
                    stats_imgs = True
                    ), name='realign_all',
                                iterfield = 'in_file')

    plot_motion = pe.MapNode(interface=fsl.PlotMotionParams(in_source='fsl'),
                            name='plot_motion',
                            iterfield=['in_file'])

    rename = pe.Node(niu.Rename(format_string='session_EPI_space',
                            keep_ext=True),
                    name='namer')


    ### Workflow to be returned
    motion_correction_workflow = pe.Workflow(name=name)

    motion_correction_workflow.connect(input_node, 'which_file_is_EPI_space', EPI_file_selector_node, 'which_file')
    motion_correction_workflow.connect(input_node, 'in_files', EPI_file_selector_node, 'in_files')

    motion_correction_workflow.connect(EPI_file_selector_node, 'raw_EPI_space_file', motion_correct_EPI_space, 'in_file')
    motion_correction_workflow.connect(motion_correct_EPI_space, 'out_file', mean_bold, 'in_file')
    motion_correction_workflow.connect(mean_bold, 'out_file', motion_correct_all, 'ref_file')
    motion_correction_workflow.connect(input_node, 'in_files', motion_correct_all, 'in_file')

    motion_correction_workflow.connect(mean_bold, 'out_file', output_node, 'EPI_space_file')
    motion_correction_workflow.connect(motion_correct_all, 'par_file', output_node, 'motion_correction_parameters')
    motion_correction_workflow.connect(motion_correct_all, 'out_file', output_node, 'motion_corrected_files')

    ########################################################################################
    # Plot the estimated motion parameters
    ########################################################################################

    plot_motion.iterables = ('plot_type', ['rotations', 'translations'])
    motion_correction_workflow.connect(motion_correct_all, 'par_file', plot_motion, 'in_file')
    motion_correction_workflow.connect(plot_motion, 'out_file', output_node, 'motion_correction_plots')

    ########################################################################################
    # outputs via datasink
    ########################################################################################
    datasink = pe.Node(nio.DataSink(), name='sinker')

    # first link the workflow's output_directory into the datasink.
    motion_correction_workflow.connect(input_node, 'output_directory', datasink, 'base_directory')
    # and the rest

    motion_correction_workflow.connect(mean_bold, 'out_file', rename, 'in_file')
    motion_correction_workflow.connect(rename, 'out_file', datasink, 'reg')

    motion_correction_workflow.connect(motion_correct_all, 'out_file', datasink, 'mcf')
    motion_correction_workflow.connect(motion_correct_all, 'par_file', datasink, 'motion_pars')
    motion_correction_workflow.connect(plot_motion, 'out_file', datasink, 'motion_plots')

    return motion_correction_workflow

