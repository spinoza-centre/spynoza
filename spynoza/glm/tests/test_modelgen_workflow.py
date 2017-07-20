from __future__ import absolute_import
import os.path as op
import pytest
from ..workflows import create_modelgen_workflow
from ... import test_data_path

test_data_path = op.join(test_data_path, 'sub-0020')


@pytest.mark.glm
def test_create_modelgen_workflow():

    modelgen_wf = create_modelgen_workflow()
    modelgen_wf.base_dir = '/tmp/spynoza/workingdir'
    modelgen_wf.inputs.inputspec.events_file = [op.join(test_data_path, 'func', 'sub-0020_task-harriri_events.tsv'),
                                                op.join(test_data_path, 'func', 'sub-0020_task-wm_events.tsv')]
    modelgen_wf.inputs.inputspec.func_file = [op.join(test_data_path, 'func', 'sub-0020_task-harriri_bold_cut_mcf.nii.gz'),
                                                op.join(test_data_path, 'func', 'sub-0020_task-wm_bold_cut_mcf.nii.gz')]
    modelgen_wf.inputs.inputspec.TR = 2.0
    modelgen_wf.inputs.inputspec.single_trial = False
    modelgen_wf.inputs.inputspec.sort_by_onset = False
    modelgen_wf.inputs.inputspec.exclude = None
    modelgen_wf.inputs.inputspec.confound_file = [op.join(test_data_path, 'func', 'sub-0020_task-harriri_bold_confounds.tsv'),
                                                  op.join(test_data_path, 'func', 'sub-0020_task-wm_bold_confounds.tsv')]
    modelgen_wf.inputs.inputspec.which_confounds = ['X', 'Y', 'Z', 'RotX', 'RotY', 'RotZ']
    modelgen_wf.inputs.inputspec.extend_motion_pars = False
    modelgen_wf.run()
