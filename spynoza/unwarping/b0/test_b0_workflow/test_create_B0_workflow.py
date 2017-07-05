import pytest
import os.path as op
from ..workflows import create_B0_workflow
from .... import test_data_path

test_data_path = op.join(test_data_path, 'sub-0020')

@pytest.mark.b0
def test_create_B0_workflow():

    b0_wf = create_B0_workflow()
    b0_wf.base_dir = '/tmp/spynoza/workingdir'
    b0_wf.inputs.inputspec.in_files = [op.join(test_data_path, 'func', 'sub-0020_task-harriri_bold_cut_mcf.nii.gz'),
                                       op.join(test_data_path, 'func', 'sub-0020_task-wm_bold_cut_mcf.nii.gz')]
    b0_wf.inputs.inputspec.fieldmap_mag = op.join(test_data_path, 'fmap', 'sub-0020_B0_magnitude.nii.gz')
    b0_wf.inputs.inputspec.fieldmap_pha = op.join(test_data_path, 'fmap', 'sub-0020_B0_phasediff.nii.gz')
    b0_wf.inputs.inputspec.wfs = 12.223
    b0_wf.inputs.inputspec.epi_factor = 35.0
    b0_wf.inputs.inputspec.acceleration = 3.0
    b0_wf.inputs.inputspec.te_diff = 0.005
    b0_wf.inputs.inputspec.phase_encoding_direction = 'y'
    b0_wf.run()
