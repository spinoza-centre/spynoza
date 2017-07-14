from __future__ import absolute_import
import pytest
import os.path as op
from ..workflows import create_confound_workflow
from ... import test_data_path

test_data_path = op.join(test_data_path, 'sub-0020')

@pytest.mark.confound
def test_create_confound_workflow():
    confound_wf = create_confound_workflow()
    confound_wf.base_dir = '/tmp/spynoza/workingdir'
    confound_wf.inputs.inputspec.in_file = [op.join(test_data_path, 'func', 'sub-0020_task-harriri_bold_cut_mcf.nii.gz'),
                                            op.join(test_data_path, 'func', 'sub-0020_task-wm_bold_cut_mcf.nii.gz')]
    confound_wf.inputs.inputspec.fast_files = [op.join(test_data_path, 'anat', 'sub-0020_T1w_prob_0.nii.gz'),
                                             op.join(test_data_path, 'anat', 'sub-0020_T1w_prob_1.nii.gz'),
                                             op.join(test_data_path, 'anat', 'sub-0020_T1w_prob_2.nii.gz')]
    confound_wf.inputs.inputspec.highres2epi_mat = op.join(test_data_path, 'highres2example_func.mat')
    confound_wf.inputs.inputspec.par_file = [op.join(test_data_path, 'func', 'sub-0020_task-harriri_bold_cut_mcf.par'),
                                           op.join(test_data_path, 'func', 'sub-0020_task-wm_bold_cut_mcf.par')]
    confound_wf.inputs.inputspec.n_comp_acompcor = 5
    confound_wf.inputs.inputspec.n_comp_tcompcor = 5
    confound_wf.inputs.inputspec.output_directory = '/tmp/spynoza'
    confound_wf.inputs.inputspec.sub_id = 'sub-0020'
    confound_wf.run()