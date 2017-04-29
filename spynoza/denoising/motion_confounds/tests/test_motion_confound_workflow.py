import pytest
import os.path as op
from ..workflows import create_motion_confound_workflow
from .... import test_data_path

@pytest.mark.confounds
def test_create_motion_correction_workflow():
    motion_confound_wf = create_motion_confound_workflow(order=2)
    motion_confound_wf.base_dir = '/tmp/spynoza/workingdir'
    motion_confound_wf.inputs.inputspec.par_file = op.join(test_data_path, 'sub-0020_gstroop_cut_mcf.par')
    motion_confound_wf.inputs.inputspec.output_directory = '/tmp/spynoza'
    motion_confound_wf.inputs.inputspec.sub_id = 'sub-0020'
    motion_confound_wf.run()

    datasink = op.join(motion_confound_wf.inputs.inputspec.output_directory,
                       motion_confound_wf.inputs.inputspec.sub_id, 'confounds')

    assert op.isfile(op.join(datasink, 'all_motion_confounds.tsv'))