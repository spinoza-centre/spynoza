from __future__ import absolute_import
import os.path as op
import pytest
import sys
from ..workflows import create_firstlevel_workflow_FEAT
from .... import test_data_path

test_data_path = op.join(test_data_path, 'sub-0020')
PYTHON_VERSION = sys.version_info[0]


@pytest.mark.skipif(PYTHON_VERSION > 2, reason="FSL FEAT requires python 2")
@pytest.mark.glmfeat
@pytest.mark.parametrize('extend_motion_pars', [True, False])
def test_create_firstlevel_workflow_FEAT(extend_motion_pars):

    firstlevel_wf = create_firstlevel_workflow_FEAT()
    firstlevel_wf.base_dir = '/tmp/spynoza/workingdir'
    firstlevel_wf.inputs.inputspec.events_file = [op.join(test_data_path, 'func', 'sub-0020_task-harriri_events.tsv'),
                                                  op.join(test_data_path, 'func', 'sub-0020_task-wm_events.tsv')]
    
    firstlevel_wf.inputs.inputspec.single_trial = False
    firstlevel_wf.inputs.inputspec.sort_by_onset = False
    firstlevel_wf.inputs.inputspec.exclude = None
    firstlevel_wf.inputs.inputspec.func_file = [op.join(test_data_path, 'func', 'sub-0020_task-harriri_bold_cut_mcf.nii.gz'),
                                                op.join(test_data_path, 'func', 'sub-0020_task-wm_bold_cut_mcf.nii.gz')]
    firstlevel_wf.inputs.inputspec.TR = 2.0
    firstlevel_wf.inputs.inputspec.confound_file = [op.join(test_data_path, 'func', 'sub-0020_task-harriri_bold_confounds.tsv'),
                                                    op.join(test_data_path, 'func', 'sub-0020_task-wm_bold_confounds.tsv')]
    firstlevel_wf.inputs.inputspec.which_confounds = ['X', 'Y', 'Z', 'RotX', 'RotY', 'RotZ']
    firstlevel_wf.inputs.inputspec.extend_motion_pars = extend_motion_pars
    firstlevel_wf.inputs.inputspec.hp_filter = 100
    firstlevel_wf.inputs.inputspec.hrf_base = {'dgamma': {'derivs': True}}
    firstlevel_wf.inputs.inputspec.output_directory = '/tmp/spynoza/firstlevelfeat'

    firstlevel_wf.inputs.inputspec.sub_id = 'sub-0020'
    firstlevel_wf.inputs.inputspec.model_serial_correlations = False
    contrast_harriri = ('Emotion>Control', 'T', ['emotion', 'control'], [1., -1.])
    contrast_wm = ('Active>Passive', 'T', ['active', 'passive'], [1., -1.])
    firstlevel_wf.inputs.inputspec.contrasts = [[contrast_harriri], [contrast_wm]]
    firstlevel_wf.run()
