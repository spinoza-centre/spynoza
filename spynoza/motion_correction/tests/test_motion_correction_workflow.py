import pytest
import shutil
import os
import os.path as op
from glob import glob
from ..workflows import create_motion_correction_workflow
from ... import test_data_path, root_dir


@pytest.fixture(scope="module", autouse=True)
def setup():
    print('Setup ...')
    yield None
    print('teardown ...')
    shutil.rmtree(op.join('/tmp/spynoza/workingdir', 'moco'))
    [os.remove(f) for f in glob(op.join(root_dir, 'crash*pklz'))]


#@pytest.mark.parametrize("method", ['FSL', 'AFNI'])
@pytest.mark.moco
def test_create_motion_correction_workflow(method='FSL'):
    moco_wf = create_motion_correction_workflow(method=method)
    moco_wf.base_dir = '/tmp/spynoza/workingdir'
    moco_wf.inputs.inputspec.in_files = [op.join(test_data_path, 'sub-0020_gstroop_cut.nii.gz')]#,
                                        # op.join(test_data_path, 'sub-0020_anticipation_cut.nii.gz')]
    moco_wf.inputs.inputspec.output_directory = '/tmp/spynoza'
    moco_wf.inputs.inputspec.sub_id = 'sub-0020'
    moco_wf.inputs.inputspec.tr = 2.0
    moco_wf.inputs.inputspec.which_file_is_EPI_space = 'first'
    moco_wf.run()

    datasink = op.join(moco_wf.inputs.inputspec.output_directory,
                       moco_wf.inputs.inputspec.sub_id, 'mcf')
    for f in moco_wf.inputs.inputspec.in_files:

        # ToDo: fix ugly extensions
        assert(op.isfile(op.join(datasink, op.basename(f).replace('.nii.gz', '_mcf.nii.gz'))))
        assert(op.isfile(op.join(datasink, 'motion_pars',
                                 op.basename(f).replace('.nii.gz', '_mcf.nii.gz.par'))))
        assert (op.isfile(op.join(datasink, 'motion_plots',
                                  op.basename(f).replace('.nii.gz', '_mcf.nii.gz_rot.png'))))
        assert (op.isfile(op.join(datasink, 'motion_plots',
                                  op.basename(f).replace('.nii.gz', '_mcf.nii.gz_rot.png'))))