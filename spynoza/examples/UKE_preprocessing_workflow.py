def create_preprocessing_workflow(analysis_parameters, name='yesno_3T'):
    import os.path as op
    import nipype.pipeline as pe
    from nipype.interfaces import fsl
    from nipype.interfaces.utility import Function, Merge, IdentityInterface
    from nipype.interfaces.io import SelectFiles, DataSink

    # Importing of custom nodes from spynoza packages; assumes that spynoza is installed:
    # pip install git+https://github.com/spinoza-centre/spynoza.git@develop
    from spynoza.utils import get_scaninfo, pickfirst, average_over_runs, set_nifti_intercept_slope
    from spynoza.uniformization.workflows import create_non_uniformity_correct_4D_file
    from spynoza.unwarping.b0.workflows import create_B0_workflow
    from spynoza.motion_correction.workflows import create_motion_correction_workflow
    from spynoza.registration.workflows import create_registration_workflow
    from spynoza.filtering.nodes import sgfilter
    from spynoza.conversion.nodes import psc
    from spynoza.denoising.retroicor.workflows import create_retroicor_workflow
    from spynoza.masking.workflows import create_masks_from_surface_workflow
    from spynoza.glm.nodes import fit_nuisances
    
    ########################################################################################
    # nodes
    ########################################################################################

    input_node = pe.Node(IdentityInterface(
                fields=['raw_directory', 
                    'output_directory', 
                    'FS_ID', 
                    'FS_subject_dir',
                    'task',
                    'sub_id',
                    'ses_id', 
                    'topup_conf_file', 
                    'which_file_is_EPI_space',
                    'standard_file', 
                    'psc_func', 
                    'av_func', 
                    'MB_factor',
                    'tr',
                    'slice_direction',
                    'phys_sample_rate',
                    'slice_timing',
                    'slice_order',
                    'nr_dummies',
                    'hr_rvt',
                    'wfs',
                    'epi_factor',
                    'acceleration',
                    'te_diff',
                    'echo_time',
                    'phase_encoding_direction',
                    'bd_design_matrix_file',
                    'sg_filter_window_length',
                    'sg_filter_order']), name='inputspec')

    # i/o node
    datasource_templates = dict(func='{sub_id}/{ses_id}/func/*{task}*_bold.nii.gz',
                                magnitude='{sub_id}/{ses_id}/fmap/*magnitude.nii.gz',
                                phasediff='{sub_id}/{ses_id}/fmap/*phasediff.nii.gz',
                                physio='{sub_id}/{ses_id}/func/*{task}*physio.*',
                                events='{sub_id}/{ses_id}/func/*{task}*_events.pickle',
                                eye='{sub_id}/{ses_id}/func/*{task}*_eyedata.edf')
    datasource = pe.Node(SelectFiles(datasource_templates, sort_filelist = True, raise_on_empty = False), 
        name = 'datasource')

    output_node = pe.Node(IdentityInterface(fields=([
            'temporal_filtered_files', 
            'percent_signal_change_files'])), name='outputspec')

    # nodes for setting the slope/intercept of incoming niftis to (1, 0)
    # this is apparently necessary for the B0 map files
    int_slope_B0_magnitude = pe.Node(Function(input_names=['in_file'], output_names=['out_file'], function=set_nifti_intercept_slope),
                      name='int_slope_B0_magnitude')
    int_slope_B0_phasediff = pe.Node(Function(input_names=['in_file'], output_names=['out_file'], function=set_nifti_intercept_slope),
                      name='int_slope_B0_phasediff')
    
    # reorient nodes
    # reorient_epi = pe.MapNode(interface=fsl.Reorient2Std(), name='reorient_epi', iterfield=['in_file'])
    # reorient_topup = pe.MapNode(interface=fsl.Reorient2Std(), name='reorient_topup', iterfield=['in_file'])
    # reorient_B0_magnitude = pe.Node(interface=fsl.Reorient2Std(), name='reorient_B0_magnitude')
    # reorient_B0_phasediff = pe.Node(interface=fsl.Reorient2Std(), name='reorient_B0_phasediff')

    # bet_epi = pe.MapNode(interface=
    #     fsl.BET(frac=analysis_parameters['bet_f_value'], vertical_gradient = analysis_parameters['bet_g_value'],
    #             functional=True, mask = True), name='bet_epi', iterfield=['in_file'])
    
    datasink = pe.Node(DataSink(), name='sinker')
    datasink.inputs.parameterization = False
    
    ########################################################################################
    # workflow
    ########################################################################################
    
    # the actual top-level workflow
    preprocessing_workflow = pe.Workflow(name=name)
    
    # data source 
    preprocessing_workflow.connect(input_node, 'raw_directory', datasource, 'base_directory')
    preprocessing_workflow.connect(input_node, 'sub_id', datasource, 'sub_id')
    preprocessing_workflow.connect(input_node, 'ses_id', datasource, 'ses_id')
    preprocessing_workflow.connect(input_node, 'task', datasource, 'task')
    
    # and data sink
    preprocessing_workflow.connect(input_node, 'output_directory', datasink, 'base_directory')
    
    # copy raw data to output folder:
    preprocessing_workflow.connect(datasource, 'func', datasink, 'raw')
    
    # BET (we don't do this, because we expect the raw data in the bids folder to be betted
    # already for anonymization purposes)
    # preprocessing_workflow.connect(datasource, 'func', bet_epi, 'in_file')
    
    # non-uniformity correction
    # preprocessing_workflow.connect(bet_epi, 'out_file', nuc, 'in_file')
    # preprocessing_workflow.connect(datasource, 'func', nuc, 'in_file')
    
    #B0 field correction:
    if analysis_parameters['B0_or_topup'] == 'B0':
        
        # set slope/intercept to unity for B0 map
        preprocessing_workflow.connect(datasource, 'magnitude', int_slope_B0_magnitude, 'in_file')
        preprocessing_workflow.connect(datasource, 'phasediff', int_slope_B0_phasediff, 'in_file')
        
        #B0 field correction:
        B0_wf = create_B0_workflow(name = 'B0')
        preprocessing_workflow.connect(datasource, 'func', B0_wf, 'inputspec.in_files')
        preprocessing_workflow.connect(int_slope_B0_magnitude, 'out_file', B0_wf, 'inputspec.fieldmap_mag')
        preprocessing_workflow.connect(int_slope_B0_phasediff, 'out_file', B0_wf, 'inputspec.fieldmap_pha')
        preprocessing_workflow.connect(input_node, 'wfs', B0_wf, 'inputspec.wfs')
        preprocessing_workflow.connect(input_node, 'epi_factor', B0_wf, 'inputspec.epi_factor')
        preprocessing_workflow.connect(input_node, 'acceleration', B0_wf, 'inputspec.acceleration')
        preprocessing_workflow.connect(input_node, 'te_diff', B0_wf, 'inputspec.te_diff')
        preprocessing_workflow.connect(input_node, 'phase_encoding_direction', B0_wf, 'inputspec.phase_encoding_direction')
        preprocessing_workflow.connect(B0_wf, 'outputspec.field_coefs', datasink, 'B0.fieldcoef')
        preprocessing_workflow.connect(B0_wf, 'outputspec.out_files', datasink, 'B0')
        
    # motion correction
    motion_proc = create_motion_correction_workflow('moco', method=analysis_parameters['moco_method'])
    if analysis_parameters['B0_or_topup'] == 'B0':
        preprocessing_workflow.connect(B0_wf, 'outputspec.out_files', motion_proc, 'inputspec.in_files')
    elif analysis_parameters['B0_or_topup'] == 'neither':
        preprocessing_workflow.connect(bet_epi, 'out_file', motion_proc, 'inputspec.in_files')
    preprocessing_workflow.connect(input_node, 'tr', motion_proc, 'inputspec.tr')
    preprocessing_workflow.connect(input_node, 'output_directory', motion_proc, 'inputspec.output_directory')
    preprocessing_workflow.connect(input_node, 'which_file_is_EPI_space', motion_proc, 'inputspec.which_file_is_EPI_space')
    
    # registration
    reg = create_registration_workflow(analysis_parameters, name='reg')
    preprocessing_workflow.connect(input_node, 'output_directory', reg, 'inputspec.output_directory')
    preprocessing_workflow.connect(motion_proc, 'outputspec.EPI_space_file', reg, 'inputspec.EPI_space_file')
    preprocessing_workflow.connect(input_node, 'FS_ID', reg, 'inputspec.freesurfer_subject_ID')
    preprocessing_workflow.connect(input_node, 'FS_subject_dir', reg, 'inputspec.freesurfer_subject_dir')
    preprocessing_workflow.connect(input_node, 'standard_file', reg, 'inputspec.standard_file')
    
    # temporal filtering
    preprocessing_workflow.connect(input_node, 'sg_filter_window_length', sgfilter, 'window_length')
    preprocessing_workflow.connect(input_node, 'sg_filter_order', sgfilter, 'polyorder')
    preprocessing_workflow.connect(motion_proc, 'outputspec.motion_corrected_files', sgfilter, 'in_file')
    preprocessing_workflow.connect(sgfilter, 'out_file', datasink, 'tf')
    
    # node for percent signal change
    preprocessing_workflow.connect(input_node, 'psc_func', psc, 'func')
    preprocessing_workflow.connect(sgfilter, 'out_file', psc, 'in_file')
    preprocessing_workflow.connect(psc, 'out_file', datasink, 'psc')
    
    # retroicor functionality
    if analysis_parameters['perform_physio'] == 1:
        retr = create_retroicor_workflow(name = 'retroicor', order_or_timing = analysis_parameters['retroicor_order_or_timing'])
        
        # # retroicor can take the crudest form of epi file, so that it proceeds quickly
        preprocessing_workflow.connect(datasource, 'func', retr, 'inputspec.in_files')
        preprocessing_workflow.connect(datasource, 'physio', retr, 'inputspec.phys_files')
        preprocessing_workflow.connect(input_node, 'nr_dummies', retr, 'inputspec.nr_dummies')
        preprocessing_workflow.connect(input_node, 'MB_factor', retr, 'inputspec.MB_factor')
        preprocessing_workflow.connect(input_node, 'tr', retr, 'inputspec.tr')
        preprocessing_workflow.connect(input_node, 'slice_direction', retr, 'inputspec.slice_direction')
        preprocessing_workflow.connect(input_node, 'slice_timing', retr, 'inputspec.slice_timing')
        preprocessing_workflow.connect(input_node, 'slice_order', retr, 'inputspec.slice_order')
        preprocessing_workflow.connect(input_node, 'phys_sample_rate', retr, 'inputspec.phys_sample_rate')
        preprocessing_workflow.connect(input_node, 'hr_rvt', retr, 'inputspec.hr_rvt')
        
        # fit nuisances from retroicor
        # preprocessing_workflow.connect(retr, 'outputspec.evs', fit_nuis, 'slice_regressor_list')
        # preprocessing_workflow.connect(motion_proc, 'outputspec.extended_motion_correction_parameters', fit_nuis, 'vol_regressors')
        # preprocessing_workflow.connect(psc, 'out_file', fit_nuis, 'in_file')
        
        # preprocessing_workflow.connect(fit_nuis, 'res_file', av_r, 'in_files')
        
        preprocessing_workflow.connect(retr, 'outputspec.new_phys', datasink, 'phys.log')
        preprocessing_workflow.connect(retr, 'outputspec.fig_file', datasink, 'phys.figs')
        preprocessing_workflow.connect(retr, 'outputspec.evs', datasink, 'phys.evs')
        # preprocessing_workflow.connect(fit_nuis, 'res_file', datasink, 'phys.res')
        # preprocessing_workflow.connect(fit_nuis, 'rsq_file', datasink, 'phys.rsq')
        # preprocessing_workflow.connect(fit_nuis, 'beta_file', datasink, 'phys.betas')
        
        # preprocessing_workflow.connect(av_r, 'out_file', datasink, 'av_r')
    #
    #
    # ########################################################################################
    # # masking stuff if doing mri analysis
    # ########################################################################################
    #
    #     all_mask_opds = ['dc'] + analysis_parameters[u'avg_subject_RS_label_folders']
    #     all_mask_lds = [''] + analysis_parameters[u'avg_subject_RS_label_folders']
    #
    #     # loop across different folders to mask
    #     # untested as yet.
    #     masking_list = []
    #     dilate_list = []
    #     for opd, label_directory in zip(all_mask_opds,all_mask_lds):
    #         dilate_list.append(
    #             pe.MapNode(interface=fsl.maths.DilateImage(
    #                 operation = 'mean', kernel_shape = 'sphere', kernel_size = analysis_parameters['dilate_kernel_size']),
    #                 name='dilate_'+label_directory, iterfield=['in_file']))
    #
    #         masking_list.append(create_masks_from_surface_workflow(name = 'masks_from_surface_'+label_directory))
    #
    #         masking_list[-1].inputs.inputspec.label_directory = label_directory
    #         masking_list[-1].inputs.inputspec.fill_thresh = 0.005
    #         masking_list[-1].inputs.inputspec.re = '*.label'
    #
    #         preprocessing_workflow.connect(motion_proc, 'outputspec.EPI_space_file', masking_list[-1], 'inputspec.EPI_space_file')
    #         preprocessing_workflow.connect(input_node, 'output_directory', masking_list[-1], 'inputspec.output_directory')
    #         preprocessing_workflow.connect(input_node, 'FS_subject_dir', masking_list[-1], 'inputspec.freesurfer_subject_dir')
    #         preprocessing_workflow.connect(input_node, 'FS_ID', masking_list[-1], 'inputspec.freesurfer_subject_ID')
    #         preprocessing_workflow.connect(reg, 'rename_register.out_file', masking_list[-1], 'inputspec.reg_file')
    #
    #         preprocessing_workflow.connect(masking_list[-1], 'outputspec.masks', dilate_list[-1], 'in_file')
    #         preprocessing_workflow.connect(dilate_list[-1], 'out_file', datasink, 'masks.'+opd)
    #
    #     # # surface-based label import in to EPI space, but now for RS labels
    #     # these should have been imported to the subject's FS folder,
    #     # see scripts/annot_conversion.sh
    #     RS_masks_from_surface = create_masks_from_surface_workflow(name = 'RS_masks_from_surface')
    #     RS_masks_from_surface.inputs.inputspec.label_directory = analysis_parameters['avg_subject_label_folder']
    #     RS_masks_from_surface.inputs.inputspec.fill_thresh = 0.005
    #     RS_masks_from_surface.inputs.inputspec.re = '*.label'
    #
    #     preprocessing_workflow.connect(motion_proc, 'outputspec.EPI_space_file', RS_masks_from_surface, 'inputspec.EPI_space_file')
    #     preprocessing_workflow.connect(input_node, 'output_directory', RS_masks_from_surface, 'inputspec.output_directory')
    #     preprocessing_workflow.connect(input_node, 'FS_subject_dir', RS_masks_from_surface, 'inputspec.freesurfer_subject_dir')
    #     preprocessing_workflow.connect(input_node, 'FS_ID', RS_masks_from_surface, 'inputspec.freesurfer_subject_ID')
    #     preprocessing_workflow.connect(reg, 'rename_register.out_file', RS_masks_from_surface, 'inputspec.reg_file')
    #
    #     preprocessing_workflow.connect(RS_masks_from_surface, 'outputspec.masks', RS_dilate_cortex, 'in_file')
    #     preprocessing_workflow.connect(RS_dilate_cortex, 'out_file', datasink, 'masks.'+analysis_parameters['avg_subject_label_folder'])

    ########################################################################################
    # wrapping up, sending data to datasink 
    ########################################################################################

        # preprocessing_workflow.connect(bet_epi, 'out_file', datasink, 'bet.epi')
        # preprocessing_workflow.connect(bet_epi, 'mask_file', datasink, 'bet.epimask')
        # preprocessing_workflow.connect(bet_topup, 'out_file', datasink, 'bet.topup')
        # preprocessing_workflow.connect(bet_topup, 'mask_file', datasink, 'bet.topupmask')

        # preprocessing_workflow.connect(nuc, 'out_file', datasink, 'nuc')
        # preprocessing_workflow.connect(sgfilter, 'out_file', datasink, 'tf')
        # preprocessing_workflow.connect(psc, 'out_file', datasink, 'psc')
        # preprocessing_workflow.connect(datasource, 'physio', datasink, 'phys')
        
    return preprocessing_workflow


def configure_workflow(preprocessing_workflow, analysis_parameters, acquisition_parameters):
    
    import os
    
    # standard output variables
    preprocessing_workflow.inputs.inputspec.task = analysis_parameters["task"]
    preprocessing_workflow.inputs.inputspec.sub_id = analysis_parameters["sub_id"]
    preprocessing_workflow.inputs.inputspec.ses_id = analysis_parameters["ses_id"]
    preprocessing_workflow.inputs.inputspec.raw_directory = analysis_parameters["raw_data_dir"]
    preprocessing_workflow.inputs.inputspec.output_directory = os.path.join(analysis_parameters["opd"], analysis_parameters["task"], analysis_parameters["sub_id"], analysis_parameters["ses_id"])
    
    # FreeSurfer:
    preprocessing_workflow.inputs.inputspec.FS_subject_dir = analysis_parameters["FS_subject_dir"]
    preprocessing_workflow.inputs.inputspec.FS_ID = analysis_parameters["sub_FS_id"]
    
    # Unwarping:
    preprocessing_workflow.inputs.inputspec.phase_encoding_direction = acquisition_parameters['PhaseEncodingDirection']
    preprocessing_workflow.inputs.inputspec.te_diff = acquisition_parameters['EchoTime2'] - acquisition_parameters['EchoTime1']
    preprocessing_workflow.inputs.inputspec.acceleration = acquisition_parameters['SenseFactor']
    preprocessing_workflow.inputs.inputspec.epi_factor = acquisition_parameters['EpiFactor']
    preprocessing_workflow.inputs.inputspec.wfs = acquisition_parameters['WaterFatShift']
        
    # Motion correction:
    preprocessing_workflow.inputs.inputspec.which_file_is_EPI_space = analysis_parameters['which_file_is_EPI_space']

    # Registration:
    preprocessing_workflow.inputs.inputspec.standard_file = os.path.join(os.environ['FSL_DIR'], 'data/standard/MNI152_T1_1mm_brain.nii.gz')

    # Percent signal change:
    preprocessing_workflow.inputs.inputspec.psc_func = analysis_parameters['psc_func']

    # Temporal filtering setting
    preprocessing_workflow.inputs.inputspec.sg_filter_window_length = analysis_parameters['sg_filter_window_length']
    preprocessing_workflow.inputs.inputspec.sg_filter_order = analysis_parameters['sg_filter_order']

    # RETROICOR:
    preprocessing_workflow.inputs.inputspec.MB_factor = acquisition_parameters['MultiBandFactor']
    preprocessing_workflow.inputs.inputspec.nr_dummies = acquisition_parameters['NumberDummyScans']
    preprocessing_workflow.inputs.inputspec.tr = acquisition_parameters['RepetitionTime']
    preprocessing_workflow.inputs.inputspec.slice_direction = acquisition_parameters['SliceEncodingDirection']
    preprocessing_workflow.inputs.inputspec.phys_sample_rate = acquisition_parameters['PhysiologySampleRate']
    preprocessing_workflow.inputs.inputspec.slice_timing = acquisition_parameters['SliceTiming']
    preprocessing_workflow.inputs.inputspec.slice_order = acquisition_parameters['SliceOrder']
    preprocessing_workflow.inputs.inputspec.hr_rvt = analysis_parameters['hr_rvt']
    
    return preprocessing_workflow

