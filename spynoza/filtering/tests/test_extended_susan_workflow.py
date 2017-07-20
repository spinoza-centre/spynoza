from __future__ import absolute_import
import pytest
import os.path as op
from ..workflows import create_extended_susan_workflow
from ... import test_data_path

test_data_path = op.join(test_data_path, 'sub-0020')


@pytest.fixture(scope="module", autouse=True)
def setup():
    print('Setup ...')
    yield None
    print('teardown ...')
    #shutil.rmtree(op.join('/tmp/spynoza/workingdir', 'moco'))


@pytest.mark.filtering
def test_create_extended_susan_workflow(method='FSL'):
    smooth_wf = create_extended_susan_workflow(separate_masks=True)
    smooth_wf.base_dir = '/tmp/spynoza/workingdir'
    smooth_wf.inputs.inputspec.in_file = [op.join(test_data_path, 'func', 'sub-0020_task-harriri_bold_cut.nii.gz'),
                                          op.join(test_data_path, 'func', 'sub-0020_task-wm_bold_cut.nii.gz')]
    smooth_wf.inputs.inputspec.EPI_session_space = op.join(test_data_path, 'func',
                                                           'sub-0020_task-harriri_meanbold.nii.gz')
    smooth_wf.inputs.inputspec.output_directory = '/tmp/spynoza'
    smooth_wf.inputs.inputspec.sub_id = 'sub-0020'
    smooth_wf.inputs.inputspec.fwhm = 5
    smooth_wf.run()
