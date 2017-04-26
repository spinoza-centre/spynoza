import pytest
import os.path as op
from ..workflows import create_extended_susan_workflow
from ... import test_data_path, root_dir


@pytest.fixture(scope="module", autouse=True)
def setup():
    print('Setup ...')
    yield None
    print('teardown ...')
    #shutil.rmtree(op.join('/tmp/spynoza/workingdir', 'moco'))


@pytest.mark.filtering
def test_create_motion_correction_workflow(method='FSL'):
    smooth_wf = create_extended_susan_workflow(separate_masks=True)
    smooth_wf.base_dir = '/tmp/spynoza/workingdir'
    smooth_wf.inputs.inputspec.in_file = [op.join(test_data_path, 'sub-0020_gstroop_cut.nii.gz')]
    smooth_wf.inputs.inputspec.EPI_session_space = op.join(test_data_path, 'sub-0020_gstroop_meanbold.nii.gz')
    smooth_wf.inputs.inputspec.output_directory = '/tmp/spynoza'
    smooth_wf.inputs.inputspec.sub_id = 'sub-0020'
    smooth_wf.inputs.inputspec.fwhm = 5
    smooth_wf.run()
