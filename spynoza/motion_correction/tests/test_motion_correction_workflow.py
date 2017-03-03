import pytest
from spynoza.motion_correction.workflows import create_motion_correction_workflow


#@pytest.mark.parametrize("method", ['FSL', 'AFNI'])
def test_create_motion_correction_workflow(method='FSL'):
    moco_wf = create_motion_correction_workflow(method=method)
    moco_wf.base_dir = '/home/lukas'
    moco_wf.inputs.inputspec.in_files = ['/home/lukas/func_brain.nii.gz', '/home/lukas/func_brain2.nii.gz']
    moco_wf.inputs.inputspec.output_directory = '/tmp/spynoza'
    moco_wf.inputs.inputspec.sub_id = 'sub-001'
    moco_wf.inputs.inputspec.tr = 2.0
    moco_wf.inputs.inputspec.which_file_is_EPI_space = 'first'
    moco_wf.run()

if __name__ == '__main__':

    test_create_motion_correction_workflow()