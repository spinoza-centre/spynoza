from spynoza.registration.sub_workflows import create_epi_to_T1_workflow
import os
import nipype.interfaces.io as nio
import nipype.pipeline.engine as pe

os.environ['SUBJECTS_DIR'] = '/derivatives/freesurfer/'
init_reg_file = '/derivatives/manual_transformations/sub-bm/ses-odc/func/sub-bm_ses-odc_space-average_transform.mat'

wf = create_epi_to_T1_workflow(name='reg_test', init_reg_file=init_reg_file)
wf.base_dir = '/workflow_folders'

wf.inputs.inputspec.EPI_space_file = '/workflow_folders/unwarp_hires_bm/unwarp_reg_wf_0/mean_bold2/sub-bm_ses-prf_task-prf_acq-10_run-01_bold_mcf_roi_mean_av.nii.gz'
wf.inputs.inputspec.freesurfer_subject_ID = 'sub-bm'
wf.inputs.inputspec.freesurfer_subject_dir = '/derivatives/freesurfer'
wf.inputs.inputspec.T1_file = '/derivatives/masked_mp2rages/sub-bm/ses-anat/anat/sub-bm_ses-anat_space-average_desc-masked_T1w.nii.gz'

ds = pe.Node(nio.DataSink(base_directory='/derivatives/zooi'),
             name='datasink')

#wf.connect(wf.get_node('

r = wf.run()
