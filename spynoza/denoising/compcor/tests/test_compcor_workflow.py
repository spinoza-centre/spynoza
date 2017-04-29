import pytest
import os.path as op
from ..workflows import create_compcor_workflow
from .... import test_data_path

@pytest.mark.compcor
def test_create_compcor_workflow():
    compcor_wf = create_compcor_workflow()
    compcor_wf.base_dir = '/tmp/spynoza/workingdir'
    compcor_wf.inputs.inputspec.in_file = [op.join(test_data_path, 'sub-0020_gstroop_cut_mcf.nii.gz'),
                                           op.join(test_data_path,
                                                   'sub-0020_gstroop_cut_mcf.nii.gz')]
    compcor_wf.inputs.inputspec.fast_files = [op.join(test_data_path, 'sub-0020_T1w_prob_0.nii.gz'),
                                             op.join(test_data_path, 'sub-0020_T1w_prob_1.nii.gz'),
                                             op.join(test_data_path, 'sub-0020_T1w_prob_2.nii.gz')]
    compcor_wf.inputs.inputspec.highres2epi_mat = op.join(test_data_path, 'highres2example_func.mat')
    compcor_wf.inputs.inputspec.n_comp_acompcor = 5
    compcor_wf.inputs.inputspec.n_comp_tcompcor = 5
    compcor_wf.inputs.inputspec.output_directory = '/tmp/spynoza'
    compcor_wf.inputs.inputspec.sub_id = 'sub-0020'
    compcor_wf.run()