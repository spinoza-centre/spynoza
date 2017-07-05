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
    modelgen_wf.inputs.inputspec.realignment_parameters = [op.join(test_data_path, 'func', 'sub-0020_task-harriri_bold_cut_mcf.par'),
                                                op.join(test_data_path, 'func', 'sub-0020_task-wm_bold_cut_mcf.par')]
    modelgen_wf.inputs.inputspec.output_directory = '/tmp/spynoza'
    modelgen_wf.inputs.inputspec.sub_id = 'sub-0020'
    modelgen_wf.run()
