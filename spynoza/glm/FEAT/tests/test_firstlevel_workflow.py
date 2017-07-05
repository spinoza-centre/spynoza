import os.path as op
import pytest
from ..workflows import create_firstlevel_workflow
from .... import test_data_path

test_data_path = op.join(test_data_path, 'sub-0020')


@pytest.mark.glmfeat
def test_create_firstlevel_workflow():

    firstlevel_wf = create_firstlevel_workflow()
    firstlevel_wf.base_dir = '/tmp/spynoza/workingdir'
    firstlevel_wf.inputs.inputspec.events_file = [op.join(test_data_path, 'func', 'sub-0020_task-harriri_events.tsv'),
                                                  op.join(test_data_path, 'func', 'sub-0020_task-wm_events.tsv')]
    firstlevel_wf.inputs.inputspec.func_file = [op.join(test_data_path, 'func', 'sub-0020_task-harriri_bold_cut_mcf.nii.gz'),
                                                op.join(test_data_path, 'func', 'sub-0020_task-wm_bold_cut_mcf.nii.gz')]
    firstlevel_wf.inputs.inputspec.TR = 2.0
    firstlevel_wf.inputs.inputspec.realignment_parameters = [op.join(test_data_path, 'func', 'sub-0020_task-harriri_bold_cut_mcf.par'),
                                                             op.join(test_data_path, 'func', 'sub-0020_task-wm_bold_cut_mcf.par')]
    firstlevel_wf.inputs.inputspec.output_directory = '/tmp/spynoza'
    firstlevel_wf.inputs.inputspec.sub_id = 'sub-0020'
    firstlevel_wf.inputs.inputspec.model_serial_correlations = False
    contrast_harriri = ('Emotion>Control', 'T', ['emotion', 'control'], [1., -1.])
    contrast_wm = ('Active>Passive', 'T', ['active', 'passive'], [1., -1.])
    firstlevel_wf.inputs.inputspec.contrasts = [[contrast_harriri], [contrast_wm]]
    firstlevel_wf.run()
