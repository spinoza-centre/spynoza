def create_all_7T_workflow(session_info, name='all_7T'):
    import os.path as op
    import nipype.pipeline as pe
    from nipype.interfaces import fsl
    from nipype.interfaces.utility import Function, Merge, IdentityInterface
    from spynoza.nodes.utils import get_scaninfo, dyns_min_1, topup_scan_params, apply_scan_params
    from nipype.interfaces.io import SelectFiles, DataSink


    # Importing of custom nodes from spynoza packages; assumes that spynoza is installed:
    # pip install git+https://github.com/spinoza-centre/spynoza.git@master
    from spynoza.nodes.filtering import apply_sg_filter
    from spynoza.nodes.utils import get_scaninfo, pickfirst, percent_signal_change
    from spynoza.workflows.topup import create_topup_workflow
    from spynoza.workflows.motion_correction import create_motion_correction_workflow
    from spynoza.workflows.registration import create_registration_workflow

    input_node = pe.Node(IdentityInterface(
        fields=['raw_directory', 'output_directory', 'FS_ID', 'FS_subject_dir',
                'present_subject', 'run_nrs', 'topup_conf_file', 'which_file_is_EPI_space',
                'standard_file', 'psc_func']), name='inputspec')

    # the actual top-level workflow
    all_7T_workflow = pe.Workflow(name=name)

    # i/o node
    datasource_templates = dict(func='{present_subject}/func/*{run_nr}_bold.nii.gz',
                                topup='{present_subject}/fmap/*{run_nr}_topup.nii.gz',
                                physio='{present_subject}/func/*{run_nr}_physio.log',
                                events='{present_subject}/func/*{run_nr}_events.pickle',
                                eye='{present_subject}/func/*{run_nr}_eyedata.edf',
                                anat='{present_subject}/anat/*_T1w.nii.gz')
    datasource = pe.Node(SelectFiles(datasource_templates, sort_filelist = True), 
    	name = 'datasource')

    all_7T_workflow.connect(input_node, 'raw_directory', datasource, 'base_directory')
    all_7T_workflow.connect(input_node, 'run_nrs', datasource, 'run_nr')
    all_7T_workflow.connect(input_node, 'present_subject', datasource, 'present_subject')


    # topup
    tua_wf = create_topup_workflow(session_info, name = 'topup')
    all_7T_workflow.connect(input_node, 'output_directory', tua_wf, 'inputspec.output_directory')
    all_7T_workflow.connect(input_node, 'topup_conf_file', tua_wf, 'inputspec.conf_file')
    all_7T_workflow.connect(datasource, 'outputs.func', tua_wf, 'inputspec.in_files')
    all_7T_workflow.connect(datasource, 'outputs.topup', tua_wf, 'inputspec.alt_files')
    
    # debugging
    print(dir(tua_wf.outputs))
    print(tua_wf.list_node_names())
    print(tua_wf.outputs.outputspec)

    # motion correction
    motion_proc = create_motion_correction_workflow('moco')
    all_7T_workflow.connect(input_node, 'output_directory', motion_proc, 'inputspec.output_directory')
    all_7T_workflow.connect(input_node, 'which_file_is_EPI_space', motion_proc, 'inputspec.which_file_is_EPI_space')
    all_7T_workflow.connect(tua_wf, 'outputspec.out_files', motion_proc, 'inputspec.in_files')


    # registration
    reg = create_registration_workflow(session_info, name = 'reg')
    all_7T_workflow.connect(motion_proc, 'outputspec.EPI_space_file', reg, 'inputspec.EPI_space_file')
    all_7T_workflow.connect(input_node, 'output_directory', reg, 'inputspec.output_directory')
    all_7T_workflow.connect(input_node, 'FS_ID', reg, 'inputspec.freesurfer_subject_ID')
    all_7T_workflow.connect(input_node, 'FS_subject_dir', reg, 'inputspec.freesurfer_subject_dir')
    all_7T_workflow.connect(input_node, 'standard_file', reg, 'inputspec.standard_file')
    # the T1_file entry could be empty sometimes, depending on the output of the
    # datasource. Check this.
    all_7T_workflow.connect(datasource, ('anat', pickfirst), reg, 'inputspec.T1_file')	


    # node for temporal filtering
    sgfilter = pe.MapNode(Function(input_names=['in_file'],
                                    output_names=['out_file'],
                                    function=apply_sg_filter),
                      name='sgfilter', iterfield=['in_file'])
    all_7T_workflow.connect(motion_proc, 'outputspec.motion_corrected_files', sgfilter, 'in_file')


    # node for percent signal change
    psc = pe.MapNode(Function(input_names=['in_file', 'func'],
                                    output_names=['out_file'],
                                    function=percent_signal_change),
                      name='percent_signal_change', iterfield=['in_file'])
    all_7T_workflow.connect(input_node, 'psc_func', psc, 'func')
    all_7T_workflow.connect(sgfilter, 'out_file', psc, 'in_file')



    return all_7T_workflow
