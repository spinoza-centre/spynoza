def create_all_7T_workflow(analysis_info, name='all_7T'):
    import os.path as op
    import nipype.pipeline as pe
    from nipype.interfaces import fsl
    from nipype.interfaces.utility import Function, Merge, IdentityInterface
    from spynoza.nodes.utils import get_scaninfo, dyns_min_1, topup_scan_params, apply_scan_params
    from nipype.interfaces.io import SelectFiles, DataSink


    # Importing of custom nodes from spynoza packages; assumes that spynoza is installed:
    # pip install git+https://github.com/spinoza-centre/spynoza.git@master
    from spynoza.nodes.filtering import savgol_filter
    from spynoza.nodes.utils import get_scaninfo, pickfirst, percent_signal_change, average_over_runs, pickle_to_json
    from spynoza.workflows.topup_unwarping import create_topup_workflow
    from spynoza.workflows.B0_unwarping import create_B0_workflow
    from spynoza.workflows.motion_correction import create_motion_correction_workflow
    from spynoza.workflows.registration import create_registration_workflow
    from spynoza.workflows.retroicor import create_retroicor_workflow
    from spynoza.nodes.fit_nuisances import fit_nuisances


    ########################################################################################
    # nodes
    ########################################################################################

    input_node = pe.Node(IdentityInterface(
                fields=['raw_directory', 
                    'output_directory', 
                    'FS_ID', 
                    'FS_subject_dir',
                    'sub_id', 
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
                    'wfs',
                    'epi_factor',
                    'acceleration',
                    'te_diff',
                    'echo_time',
                    'phase_encoding_direction']), name='inputspec')

    # i/o node
    datasource_templates = dict(func='{sub_id}/*func*.nii.gz',
                                magnitude='{sub_id}/*magnitude*.nii.gz',
                                phasediff='{sub_id}/*phasediff*.nii.gz',
                                topup='{sub_id}/*topup*.nii.gz',
                                physio='{sub_id}/*.log',
                                events='{sub_id}/*.pickle',
                                eye='{sub_id}/*.edf') # ,
                                # anat='{sub_id}/anat/*_T1w.nii.gz'
    datasource = pe.Node(SelectFiles(datasource_templates, sort_filelist = True, raise_on_empty = False), 
        name = 'datasource')

    output_node = pe.Node(IdentityInterface(fields=([
            'temporal_filtered_files', 
            'percent_signal_change_files'])), name='outputspec')

    # reorient nodes
    reorient_epi = pe.MapNode(interface=fsl.Reorient2Std(), name='reorient_epi', iterfield=['in_file'])
    reorient_topup = pe.MapNode(interface=fsl.Reorient2Std(), name='reorient_topup', iterfield=['in_file'])
    reorient_B0_magnitude = pe.Node(interface=fsl.Reorient2Std(), name='reorient_B0_magnitude')
    reorient_B0_phasediff = pe.Node(interface=fsl.Reorient2Std(), name='reorient_B0_phasediff')

    bet_epi = pe.MapNode(interface=
        fsl.BET(frac=analysis_info['bet_frac'], vertical_gradient = analysis_info['bet_vert_grad'], 
                functional=True, mask = True), name='bet_epi', iterfield=['in_file'])
    bet_topup = pe.MapNode(interface=
        fsl.BET(frac=analysis_info['bet_frac'], vertical_gradient = analysis_info['bet_vert_grad'], 
                functional=True, mask = True), name='bet_topup', iterfield=['in_file'])
    bet_moco = pe.Node(interface=
        fsl.BET(frac=analysis_info['bet_frac'], vertical_gradient = analysis_info['bet_vert_grad'], 
                functional=True, mask = True), name='bet_moco')

    # node for converting pickle files to json
    sgfilter = pe.MapNode(Function(input_names=['in_file'],
                                    output_names=['out_file'],
                                    function=savgol_filter),
                      name='sgfilter', iterfield=['in_file'])

    # node for temporal filtering
    pj = pe.MapNode(Function(input_names=['in_file'],
                                    output_names=['out_file'],
                                    function=pickle_to_json),
                      name='pj', iterfield=['in_file'])

    # node for percent signal change
    psc = pe.MapNode(Function(input_names=['in_file', 'func'],
                                    output_names=['out_file'],
                                    function=percent_signal_change),
                      name='percent_signal_change', iterfield=['in_file'])

    # node for nuisance regression
    fit_nuis = pe.MapNode(Function(input_names=['in_file', 'slice_regressor_list', 'vol_regressors'],
                                    output_names=['res_file', 'rsq_file', 'beta_file'],
                                    function=fit_nuisances),
                      name='fit_nuisances', iterfield=['in_file', 'slice_regressor_list', 'vol_regressors']) 

    # node for averaging across runs for un-retroicor'ed runs
    av = pe.Node(Function(input_names=['in_files'],
                                    output_names=['out_file'],
                                    function=average_over_runs),
                      name='average_over_runs')
    # node for averaging across runs for un-retroicor'ed runs
    av_r = pe.Node(Function(input_names=['in_files'],
                                    output_names=['out_file'],
                                    function=average_over_runs),
                      name='average_over_runs_retroicor')
   

    datasink = pe.Node(DataSink(), name='sinker')
    datasink.inputs.parameterization = False

    ########################################################################################
    # workflow
    ########################################################################################

    # the actual top-level workflow
    all_7T_workflow = pe.Workflow(name=name)

    all_7T_workflow.connect(input_node, 'raw_directory', datasource, 'base_directory')
    all_7T_workflow.connect(input_node, 'sub_id', datasource, 'sub_id')

    # behavioral pickle to json
    all_7T_workflow.connect(datasource, 'events', pj, 'in_file')

    # reorientation to standard orientation
    all_7T_workflow.connect(datasource, 'func', reorient_epi, 'in_file')
    all_7T_workflow.connect(datasource, 'topup', reorient_topup, 'in_file')
    all_7T_workflow.connect(datasource, 'magnitude', reorient_B0_magnitude, 'in_file')
    all_7T_workflow.connect(datasource, 'phasediff', reorient_B0_phasediff, 'in_file')

    # BET
    all_7T_workflow.connect(reorient_epi, 'out_file', bet_epi, 'in_file')
    all_7T_workflow.connect(reorient_topup, 'out_file', bet_topup, 'in_file')

    # topup
    tua_wf = create_topup_workflow(analysis_info, name = 'topup')
    all_7T_workflow.connect(input_node, 'output_directory', tua_wf, 'inputspec.output_directory')
    all_7T_workflow.connect(input_node, 'topup_conf_file', tua_wf, 'inputspec.conf_file')
    all_7T_workflow.connect(bet_epi, 'out_file', tua_wf, 'inputspec.in_files')
    all_7T_workflow.connect(bet_topup, 'out_file', tua_wf, 'inputspec.alt_files')
    all_7T_workflow.connect(input_node, 'epi_factor', tua_wf, 'inputspec.epi_factor')
    all_7T_workflow.connect(input_node, 'echo_time', tua_wf, 'inputspec.echo_time')
    all_7T_workflow.connect(input_node, 'phase_encoding_direction', tua_wf, 'inputspec.phase_encoding_direction')

    #B0
    B0_wf = create_B0_workflow(name = 'B0')
    all_7T_workflow.connect(bet_epi, 'out_file', B0_wf, 'inputspec.in_files')
    all_7T_workflow.connect(reorient_B0_magnitude, 'out_file', B0_wf, 'inputspec.fieldmap_mag')
    all_7T_workflow.connect(reorient_B0_phasediff, 'out_file', B0_wf, 'inputspec.fieldmap_pha')
    all_7T_workflow.connect(input_node, 'wfs', B0_wf, 'inputspec.wfs')
    all_7T_workflow.connect(input_node, 'epi_factor', B0_wf, 'inputspec.epi_factor')
    all_7T_workflow.connect(input_node, 'acceleration', B0_wf, 'inputspec.acceleration')
    all_7T_workflow.connect(input_node, 'te_diff', B0_wf, 'inputspec.te_diff')
    all_7T_workflow.connect(input_node, 'phase_encoding_direction', B0_wf, 'inputspec.phase_encoding_direction')
    
    # motion correction
    motion_proc = create_motion_correction_workflow('moco')
    all_7T_workflow.connect(input_node, 'tr', motion_proc, 'inputspec.tr')
    all_7T_workflow.connect(input_node, 'output_directory', motion_proc, 'inputspec.output_directory')
    all_7T_workflow.connect(input_node, 'which_file_is_EPI_space', motion_proc, 'inputspec.which_file_is_EPI_space')
    if analysis_info['B0_or_topup'] == 'topup':
        all_7T_workflow.connect(tua_wf, 'outputspec.out_files', motion_proc, 'inputspec.in_files')
    elif analysis_info['B0_or_topup'] == 'B0':
        all_7T_workflow.connect(B0_wf, 'outputspec.out_files', motion_proc, 'inputspec.in_files')

    # registration
    reg = create_registration_workflow(analysis_info, name = 'reg')
    all_7T_workflow.connect(input_node, 'output_directory', reg, 'inputspec.output_directory')
    all_7T_workflow.connect(motion_proc, 'outputspec.EPI_space_file', reg, 'inputspec.EPI_space_file')
    all_7T_workflow.connect(input_node, 'FS_ID', reg, 'inputspec.freesurfer_subject_ID')
    all_7T_workflow.connect(input_node, 'FS_subject_dir', reg, 'inputspec.freesurfer_subject_dir')
    all_7T_workflow.connect(input_node, 'standard_file', reg, 'inputspec.standard_file')
    # the T1_file entry could be empty sometimes, depending on the output of the
    # datasource. Check this.
    # all_7T_workflow.connect(reg, 'outputspec.T1_file', reg, 'inputspec.T1_file')    

    # BET the motion corrected EPI_space_file for global mask.
    all_7T_workflow.connect(motion_proc, 'outputspec.EPI_space_file', bet_moco, 'in_file')

    # temporal filtering
    all_7T_workflow.connect(motion_proc, 'outputspec.motion_corrected_files', sgfilter, 'in_file')

    # node for percent signal change
    all_7T_workflow.connect(input_node, 'psc_func', psc, 'func')
    all_7T_workflow.connect(sgfilter, 'out_file', psc, 'in_file')

    # connect filtering and psc results to output node 
    all_7T_workflow.connect(sgfilter, 'out_file', output_node, 'temporal_filtered_files')
    all_7T_workflow.connect(psc, 'out_file', output_node, 'percent_signal_change_files')

    # averaging across runs
    all_7T_workflow.connect(input_node, 'av_func', av, 'func')
    all_7T_workflow.connect(psc, 'out_file', av, 'in_files')

    # retroicor functionality
    retr = create_retroicor_workflow(name = 'retroicor', order_or_timing = analysis_info['retroicor_order_or_timing'])

    # retroicor can take the crudest form of epi file, so that it proceeds quickly
    all_7T_workflow.connect(reorient_epi, 'out_file', retr, 'inputspec.in_files')

    all_7T_workflow.connect(datasource, 'physio', retr, 'inputspec.phys_files')
    all_7T_workflow.connect(input_node, 'nr_dummies', retr, 'inputspec.nr_dummies')
    all_7T_workflow.connect(input_node, 'MB_factor', retr, 'inputspec.MB_factor')
    all_7T_workflow.connect(input_node, 'tr', retr, 'inputspec.tr')
    all_7T_workflow.connect(input_node, 'slice_direction', retr, 'inputspec.slice_direction')
    all_7T_workflow.connect(input_node, 'slice_timing', retr, 'inputspec.slice_timing')
    all_7T_workflow.connect(input_node, 'slice_order', retr, 'inputspec.slice_order')
    all_7T_workflow.connect(input_node, 'phys_sample_rate', retr, 'inputspec.phys_sample_rate')

    # fit nuisances from retroicor
    # for now, I won't actually fit the retroicor stuff
    # all_7T_workflow.connect(retr, 'outputspec.evs', fit_nuis, 'slice_regressor_list')
    # all_7T_workflow.connect(motion_proc, 'outputspec.extended_motion_correction_parameters', fit_nuis, 'vol_regressors')
    # all_7T_workflow.connect(psc, 'out_file', fit_nuis, 'in_file')

    # all_7T_workflow.connect(fit_nuis, 'res_file', av_r, 'in_files')

    ########################################################################################
    # outputs via datasink
    ########################################################################################

    all_7T_workflow.connect(input_node, 'output_directory', datasink, 'base_directory')

    # sink out events and eyelink files
    all_7T_workflow.connect(pj, 'out_file', datasink, 'events')
    all_7T_workflow.connect(datasource, 'eye', datasink, 'eye')

    all_7T_workflow.connect(bet_epi, 'out_file', datasink, 'bet.epi')
    all_7T_workflow.connect(bet_epi, 'mask_file', datasink, 'bet.epimask')
    all_7T_workflow.connect(bet_topup, 'out_file', datasink, 'bet.topup')
    all_7T_workflow.connect(bet_topup, 'mask_file', datasink, 'bet.topupmask')
    all_7T_workflow.connect(bet_moco, 'mask_file', datasink, 'bet')

    all_7T_workflow.connect(tua_wf, 'outputspec.field_coefs', datasink, 'topup.fieldcoef')
    all_7T_workflow.connect(tua_wf, 'outputspec.out_files', datasink, 'topup.unwarped')

    all_7T_workflow.connect(B0_wf, 'outputspec.field_coefs', datasink, 'B0.fieldcoef')
    all_7T_workflow.connect(B0_wf, 'outputspec.out_files', datasink, 'B0.unwarped')

    all_7T_workflow.connect(sgfilter, 'out_file', datasink, 'tf')
    all_7T_workflow.connect(psc, 'out_file', datasink, 'psc')
    all_7T_workflow.connect(av, 'out_file', datasink, 'av')

    all_7T_workflow.connect(retr, 'outputspec.new_phys', datasink, 'phys.log')
    all_7T_workflow.connect(retr, 'outputspec.fig_file', datasink, 'phys.figs')
    all_7T_workflow.connect(retr, 'outputspec.evs', datasink, 'phys.evs')

    # all_7T_workflow.connect(fit_nuis, 'res_file', datasink, 'phys.res')
    # all_7T_workflow.connect(fit_nuis, 'rsq_file', datasink, 'phys.rsq')
    # all_7T_workflow.connect(fit_nuis, 'beta_file', datasink, 'phys.betas')

    # all_7T_workflow.connect(av_r, 'out_file', datasink, 'av_r')


    return all_7T_workflow
