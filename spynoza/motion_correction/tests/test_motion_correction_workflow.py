from __future__ import absolute_import
import pytest
import os.path as op
import shutil
import socket
from ..workflows import create_motion_correction_workflow
from ... import test_data_path

test_data_path = op.join(test_data_path, 'sub-0020')


@pytest.fixture(scope="module", autouse=True)
def setup():
    print('Setup ...')
    yield None
    print('teardown ...')
    #shutil.rmtree(op.join('/tmp/spynoza/workingdir', 'moco'))

# Only test AFNI volreg if not on UvA desktop (weird GLX error)
hostname = socket.gethostname()
methods = ['FSL', 'AFNI'] if hostname != 'uva' else ['FSL']


@pytest.mark.parametrize("method", methods)
@pytest.mark.moco
def test_create_motion_correction_workflow(method):
    moco_wf = create_motion_correction_workflow(method=method)
    moco_wf.base_dir = '/tmp/spynoza/workingdir'
    moco_wf.inputs.inputspec.in_files = [op.join(test_data_path, 'func', 'sub-0020_task-harriri_bold_cut.nii.gz'),
                                         op.join(test_data_path, 'func', 'sub-0020_task-wm_bold_cut.nii.gz')]
    moco_wf.inputs.inputspec.output_directory = '/tmp/spynoza'
    moco_wf.inputs.inputspec.sub_id = 'sub-0020'
    moco_wf.inputs.inputspec.tr = 2.0
    moco_wf.inputs.inputspec.which_file_is_EPI_space = 'first'
    moco_wf.run()

    datasink = op.join(moco_wf.inputs.inputspec.output_directory,
                       moco_wf.inputs.inputspec.sub_id, 'mcf')
    for f in moco_wf.inputs.inputspec.in_files:

        assert(op.isfile(op.join(datasink, op.basename(f).replace('.nii.gz', '_mcf.nii.gz'))))
        assert(op.isfile(op.join(datasink, 'motion_pars',
                                 op.basename(f).replace('.nii.gz', '_mcf.par'))))
        assert (op.isfile(op.join(datasink, 'motion_plots',
                                  op.basename(f).replace('.nii.gz', '_mcf_rot.png'))))
        assert (op.isfile(op.join(datasink, 'motion_plots',
                                  op.basename(f).replace('.nii.gz', '_mcf_rot.png'))))