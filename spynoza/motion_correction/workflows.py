import nipype.pipeline as pe
import nipype.interfaces.fsl as fsl
import nipype.interfaces.afni.preprocess as afni
import nipype.interfaces.io as nio
from nipype.interfaces.utility import Rename
from nipype.interfaces.utility import IdentityInterface
import nipype.interfaces.utility as niu
from ..utils import EPI_file_selector, Set_postfix, Remove_extension, ComputeEPIMask


def create_motion_correction_workflow(name='moco',
                                      method='AFNI',
                                      extend_moco_params=False,
                                      output_mask=False,
                                      lightweight=False):
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


    if lightweight and (method == 'AFNI'):
        raise NotImplementedError('lightweight workflow currently only supports FSL')

    ### NODES
    in_fields = ['in_files', 'which_file_is_EPI_space']

    if not lightweight:
        in_fields += ['output_directory', 'sub_id', 'tr']
    
    input_node = pe.Node(IdentityInterface(fields=in_fields), 
                                            name='inputspec')


    out_fields = ['motion_corrected_files', 'EPI_space_file']
    
    if not lightweight:
        out_fields += ['motion_correction_plots', 'motion_correction_parameters',
                  'extended_motion_correction_parameters', 'new_motion_correction_parameters']

    if output_mask:
        out_fields += ['EPI_space_mask']

    output_node = pe.Node(IdentityInterface(fields=out_fields), 
                                            name='outputspec')

    ########################################################################################
    # Invariant nodes
    ########################################################################################

    EPI_file_selector_node = pe.Node(interface=EPI_file_selector, name='EPI_file_selector_node')
    mean_bold = pe.Node(interface=fsl.maths.MeanImage(dimension='T'), name='mean_space')
    rename_mean_bold = pe.Node(niu.Rename(format_string='session_EPI_space', keep_ext=True),
                                name='rename_mean_bold')

    ########################################################################################
    # Workflow
    ########################################################################################

    motion_correction_workflow = pe.Workflow(name=name)
    motion_correction_workflow.connect(input_node, 'which_file_is_EPI_space',
                                       EPI_file_selector_node, 'which_file')
    motion_correction_workflow.connect(input_node, 'in_files',
                                       EPI_file_selector_node, 'in_files')

    ########################################################################################
    # outputs via datasink
    ########################################################################################

    if not lightweight:
        datasink = pe.Node(nio.DataSink(), name='sinker')
        datasink.inputs.parameterization = False

        # first link the workflow's output_directory into the datasink.
        motion_correction_workflow.connect(input_node, 'output_directory', datasink,
                                           'base_directory')
        motion_correction_workflow.connect(input_node, 'sub_id', datasink,
                                           'container')

    ########################################################################################
    # FSL MCFlirt
    ########################################################################################
    # new approach, which should aid in the joint motion correction of
    # multiple sessions together, by pre-registering each run.
    # the strategy would be to, for each run, take the first TR
    # and FLIRT-align (6dof) it to the EPI_space file.
    # then we can use this as an --infile argument to mcflirt.

    if method == 'FSL':

        if not lightweight:
            rename_motion_files = pe.MapNode(niu.Rename(keep_ext=False),
                                             name='rename_motion_files',
                                             iterfield=['in_file', 'format_string'])

            remove_niigz_ext = pe.MapNode(interface=Remove_extension,
                                          name='remove_niigz_ext',
                                          iterfield=['in_file'])

        motion_correct_EPI_space = pe.Node(interface=fsl.MCFLIRT(
            cost='normcorr',
            interpolation='sinc',
            mean_vol=True
        ), name='motion_correct_EPI_space')

        motion_correct_all = pe.MapNode(interface=fsl.MCFLIRT(save_mats=True,
                                                              save_plots=True,
                                                              cost='normcorr',
                                                              interpolation='sinc',
                                                              stats_imgs=True),
                                        name='motion_correct_all',
                                        iterfield=['in_file'])

        if not lightweight:
            plot_motion = pe.MapNode(
                interface=fsl.PlotMotionParams(in_source='fsl'),
                name='plot_motion',
                iterfield=['in_file'])

            if extend_moco_params:
                # make extend_motion_pars node here
                # extend_motion_pars = pe.MapNode(Function(input_names=['moco_par_file', 'tr'], output_names=['new_out_file', 'ext_out_file'],
                # function=_extend_motion_parameters), name='extend_motion_pars', iterfield = ['moco_par_file'])
                pass
        
        # create reference:
        motion_correction_workflow.connect(EPI_file_selector_node, 'out_file', motion_correct_EPI_space, 'in_file')
        motion_correction_workflow.connect(motion_correct_EPI_space, 'out_file', mean_bold, 'in_file')
        motion_correction_workflow.connect(mean_bold, 'out_file', motion_correct_all, 'ref_file')

        # motion correction across runs
        motion_correction_workflow.connect(input_node, 'in_files', motion_correct_all, 'in_file')

        # output node:
        motion_correction_workflow.connect(mean_bold, 'out_file', output_node, 'EPI_space_file')
        motion_correction_workflow.connect(motion_correct_all, 'out_file', output_node, 'motion_corrected_files')


    ########################################################################################
    # Plot the estimated motion parameters
    ########################################################################################

    if not lightweight:
        # rename:
        motion_correction_workflow.connect(mean_bold, 'out_file', rename_mean_bold, 'in_file')
        motion_correction_workflow.connect(motion_correct_all, 'par_file', rename_motion_files, 'in_file')
        motion_correction_workflow.connect(motion_correct_all, 'par_file', remove_niigz_ext, 'in_file')
        motion_correction_workflow.connect(remove_niigz_ext, 'out_file', rename_motion_files, 'format_string')
        
        # plots:
        plot_motion.iterables = ('plot_type', ['rotations', 'translations'])
        motion_correction_workflow.connect(rename_motion_files, 'out_file', plot_motion, 'in_file')
        motion_correction_workflow.connect(plot_motion, 'out_file', output_node, 'motion_correction_plots')
    
        motion_correction_workflow.connect(rename_motion_files, 'out_file', output_node, 'motion_correction_parameters')
    
        # datasink:
        motion_correction_workflow.connect(rename_mean_bold, 'out_file', datasink, 'reg')
        motion_correction_workflow.connect(motion_correct_all, 'out_file', datasink, 'mcf')
        motion_correction_workflow.connect(rename_motion_files, 'out_file', datasink, 'mcf.motion_pars')
        motion_correction_workflow.connect(plot_motion, 'out_file', datasink, 'mcf.motion_plots')
        
    ########################################################################################
    # AFNI 3DVolReg
    ########################################################################################
    # for speed, we use AFNI's 3DVolReg brute-force.
    # this loses plotting of motion parameters but increases speed
    # we hold on to the same setup, first moco the selected run
    # and then moco everything to that image, but without the
    # intermediate FLIRT step.

    if method == 'AFNI':
        motion_correct_EPI_space = pe.Node(interface=afni.Volreg(outputtype='NIFTI_GZ',
                                                                zpad=5,
                                                                args=' -cubic '  # -twopass -Fourier
                                                                ), 
                                            name='motion_correct_EPI_space')

        motion_correct_all = pe.MapNode(interface=afni.Volreg(outputtype='NIFTI_GZ',
                                                                zpad=5,
                                                                args=' -cubic '  # -twopass
                                                                ), 
                                        name='motion_correct_all',
                                        iterfield=['in_file'])

        # for renaming *_volreg.nii.gz to *_mcf.nii.gz
        set_postfix_mcf = pe.MapNode(interface=Set_postfix,
                                     name='set_postfix_mcf', iterfield=['in_file'])
        set_postfix_mcf.inputs.postfix = 'mcf'

        rename_volreg = pe.MapNode(interface=Rename(keep_ext=True), 
                                    name='rename_volreg',
                                    iterfield=['in_file', 'format_string'])

        # curate for moco between sessions
        motion_correction_workflow.connect(EPI_file_selector_node, 'out_file', motion_correct_EPI_space, 'in_file')
        motion_correction_workflow.connect(motion_correct_EPI_space, 'out_file', mean_bold, 'in_file')

        # motion correction across runs
        motion_correction_workflow.connect(input_node, 'in_files', motion_correct_all, 'in_file')
        motion_correction_workflow.connect(mean_bold, 'out_file', motion_correct_all, 'basefile')
        # motion_correction_workflow.connect(mean_bold, 'out_file', motion_correct_all, 'rotparent')
        # motion_correction_workflow.connect(mean_bold, 'out_file', motion_correct_all, 'gridparent')

        # output node:
        motion_correction_workflow.connect(mean_bold, 'out_file', output_node, 'EPI_space_file')
        motion_correction_workflow.connect(motion_correct_all, 'md1d_file', output_node, 'max_displacement_info')
        motion_correction_workflow.connect(motion_correct_all, 'oned_file', output_node, 'motion_correction_parameter_info')
        motion_correction_workflow.connect(motion_correct_all, 'oned_matrix_save', output_node, 'motion_correction_parameter_matrix')
        motion_correction_workflow.connect(input_node, 'in_files', set_postfix_mcf, 'in_file')
        motion_correction_workflow.connect(set_postfix_mcf, 'out_file', rename_volreg, 'format_string')
        motion_correction_workflow.connect(motion_correct_all, 'out_file', rename_volreg, 'in_file')
        motion_correction_workflow.connect(rename_volreg, 'out_file', output_node, 'motion_corrected_files')


        # datasink:
        motion_correction_workflow.connect(mean_bold, 'out_file', rename_mean_bold, 'in_file')
        motion_correction_workflow.connect(rename_mean_bold, 'out_file', datasink, 'reg')
        motion_correction_workflow.connect(rename_volreg, 'out_file', datasink, 'mcf')
        motion_correction_workflow.connect(motion_correct_all, 'md1d_file', datasink, 'mcf.max_displacement_info')
        motion_correction_workflow.connect(motion_correct_all, 'oned_file', datasink, 'mcf.parameter_info')
        motion_correction_workflow.connect(motion_correct_all, 'oned_matrix_save', datasink, 'mcf.motion_pars')
        
    if output_mask:
        create_bold_mask = pe.Node(ComputeEPIMask(upper_cutoff=0.8), name='create_bold_mask')
        motion_correction_workflow.connect(motion_correct_EPI_space, 'out_file', create_bold_mask, 'in_file')
        motion_correction_workflow.connect(create_bold_mask, 'mask_file', output_node, 'EPI_space_mask')

    return motion_correction_workflow


