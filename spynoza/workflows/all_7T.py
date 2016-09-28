def create_all_7T_workflow(session_info, name='all_7T'):
    import os.path as op
    import nipype.pipeline as pe
    from nipype.interfaces import fsl
    from nipype.interfaces.utility import Function, Merge, IdentityInterface
    from spynoza.nodes.utils import get_scaninfo, dyns_min_1, topup_scan_params, apply_scan_params
    from nipype.interfaces.io import SelectFiles, DataSink


    # Importing of custom nodes from spynoza packages; assumes that spynoza is installed:
    # pip install git+https://github.com/spinoza-centre/spynoza.git@master
    from spynoza.nodes.filtering import savgol_filter
    from spynoza.nodes.utils import get_scaninfo, pickfirst, percent_signal_change, average_over_runs
    from spynoza.workflows.topup import create_topup_workflow
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
                    'nr_dummies']), name='inputspec')

    # i/o node
    datasource_templates = dict(func='{sub_id}/func/*_bold.nii.gz',
                                topup='{sub_id}/fmap/*_topup.nii.gz',
                                physio='{sub_id}/func/*_physio.log',
                                events='{sub_id}/func/*_events.pickle',
                                eye='{sub_id}/func/*_eyedata.edf') # ,
                                # anat='{sub_id}/anat/*_T1w.nii.gz'
    datasource = pe.Node(SelectFiles(datasource_templates, sort_filelist = True), 
        name = 'datasource')

    output_node = pe.Node(IdentityInterface(fields=([
            'temporal_filtered_files', 
            'percent_signal_change_files'])), name='outputspec')

    # reorient nodes
    reorient_epi = pe.MapNode(interface=fsl.Reorient2Std(), name='reorient_epi', iterfield=['in_file'])
    reorient_topup = pe.MapNode(interface=fsl.Reorient2Std(), name='reorient_topup', iterfield=['in_file'])

    bet_epi = pe.MapNode(interface=fsl.BET(frac=session_info['bet_frac'], vertical_gradient = session_info['bet_vert_grad'], functional=True, mask = True), name='bet_epi', iterfield=['in_file'])
    bet_topup = pe.MapNode(interface=fsl.BET(frac=session_info['bet_frac'], vertical_gradient = session_info['bet_vert_grad'], functional=True, mask = True), name='bet_topup', iterfield=['in_file'])


    # node for temporal filtering
    sgfilter = pe.MapNode(Function(input_names=['in_file'],
                                    output_names=['out_file'],
                                    function=savgol_filter),
                      name='sgfilter', iterfield=['in_file'])

    # node for percent signal change
    psc = pe.MapNode(Function(input_names=['in_file', 'func'],
                                    output_names=['out_file'],
                                    function=percent_signal_change),
                      name='percent_signal_change', iterfield=['in_file'])

    # node for nuisance regression
    fit_nuis = pe.MapNode(Function(input_names=['in_file', 'regressor_list'],
                                    output_names=['res_file', 'rsq_file', 'beta_file'],
                                    function=fit_nuisances),
                      name='fit_nuisances', iterfield=['in_file', 'regressor_list'])

    # node for averaging across runs
    av = pe.Node(Function(input_names=['in_files'],
                                    output_names=['out_file'],
                                    function=average_over_runs),
                      name='average_over_runs')
   

    datasink = pe.Node(DataSink(), name='sinker')
    datasink.inputs.parameterization = False

    ########################################################################################
    # workflow
    ########################################################################################

    # the actual top-level workflow
    all_7T_workflow = pe.Workflow(name=name)

    all_7T_workflow.connect(input_node, 'raw_directory', datasource, 'base_directory')
    all_7T_workflow.connect(input_node, 'sub_id', datasource, 'sub_id')

    # reorientation to standard orientation
    all_7T_workflow.connect(datasource, 'func', reorient_epi, 'in_file')
    all_7T_workflow.connect(datasource, 'topup', reorient_topup, 'in_file')

    # BET
    all_7T_workflow.connect(reorient_epi, 'out_file', bet_epi, 'in_file')
    all_7T_workflow.connect(reorient_topup, 'out_file', bet_topup, 'in_file')

    # topup
    tua_wf = create_topup_workflow(session_info, name = 'topup')
    all_7T_workflow.connect(input_node, 'output_directory', tua_wf, 'inputspec.output_directory')
    all_7T_workflow.connect(input_node, 'topup_conf_file', tua_wf, 'inputspec.conf_file')
    all_7T_workflow.connect(bet_epi, 'out_file', tua_wf, 'inputspec.in_files')
    all_7T_workflow.connect(bet_topup, 'out_file', tua_wf, 'inputspec.alt_files')
    
    # motion correction
    motion_proc = create_motion_correction_workflow('moco')
    all_7T_workflow.connect(input_node, 'output_directory', motion_proc, 'inputspec.output_directory')
    all_7T_workflow.connect(input_node, 'which_file_is_EPI_space', motion_proc, 'inputspec.which_file_is_EPI_space')
    all_7T_workflow.connect(tua_wf, 'outputspec.out_files', motion_proc, 'inputspec.in_files')

    # registration
    reg = create_registration_workflow(session_info, name = 'reg')
    all_7T_workflow.connect(input_node, 'output_directory', reg, 'inputspec.output_directory')
    all_7T_workflow.connect(motion_proc, 'outputspec.EPI_space_file', reg, 'inputspec.EPI_space_file')
    all_7T_workflow.connect(input_node, 'FS_ID', reg, 'inputspec.freesurfer_subject_ID')
    all_7T_workflow.connect(input_node, 'FS_subject_dir', reg, 'inputspec.freesurfer_subject_dir')
    all_7T_workflow.connect(input_node, 'standard_file', reg, 'inputspec.standard_file')
    # the T1_file entry could be empty sometimes, depending on the output of the
    # datasource. Check this.
    # all_7T_workflow.connect(reg, 'outputspec.T1_file', reg, 'inputspec.T1_file')    

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
    retr = create_retroicor_workflow(name = 'retroicor', order_or_timing = session_info['retroicor_order_or_timing'])

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
    all_7T_workflow.connect(retr, 'outputspec.evs', fit_nuis, 'regressor_list')
    all_7T_workflow.connect(psc, 'out_file', fit_nuis, 'in_file')


    ########################################################################################
    # outputs via datasink
    ########################################################################################

    all_7T_workflow.connect(input_node, 'output_directory', datasink, 'base_directory')

    all_7T_workflow.connect(bet_epi, 'out_file', datasink, 'bet.epi')
    all_7T_workflow.connect(bet_epi, 'mask_file', datasink, 'bet.epimask')
    all_7T_workflow.connect(bet_topup, 'out_file', datasink, 'bet.topup')
    all_7T_workflow.connect(bet_topup, 'mask_file', datasink, 'bet.topupmask')

    all_7T_workflow.connect(tua_wf, 'outputspec.field_coefs', datasink, 'topup.fieldcoef')
    all_7T_workflow.connect(tua_wf, 'outputspec.out_files', datasink, 'topup.unwarped')

    all_7T_workflow.connect(sgfilter, 'out_file', datasink, 'tf')
    all_7T_workflow.connect(psc, 'out_file', datasink, 'psc')
    all_7T_workflow.connect(av, 'out_file', datasink, 'av')

    all_7T_workflow.connect(retr, 'outputspec.new_phys', datasink, 'phys.log')
    all_7T_workflow.connect(retr, 'outputspec.fig_file', datasink, 'phys.figs')
    all_7T_workflow.connect(retr, 'outputspec.evs', datasink, 'phys.evs')

    all_7T_workflow.connect(fit_nuis, 'res_file', datasink, 'phys.betas')
    all_7T_workflow.connect(fit_nuis, 'rsq_file', datasink, 'phys.rsq')
    all_7T_workflow.connect(fit_nuis, 'beta_file', datasink, 'phys.res')


    return all_7T_workflow
