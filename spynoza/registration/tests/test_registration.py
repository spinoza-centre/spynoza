import pytest
import shutil
import os
import os.path as op
from glob import glob
from nipype.interfaces.fsl import Info
from ..workflows import create_registration_workflow
from ... import test_data_path, root_dir
from ...utils import set_parameters_in_nodes


@pytest.fixture(scope="module", autouse=True)
def setup():
    print('Setup ...')
    yield None
    print('teardown ...')
    shutil.rmtree(op.join('/tmp/spynoza/workingdir', 'registration'))
    [os.remove(f) for f in glob(op.join(root_dir, 'crash*pklz'))]


@pytest.mark.registration
def test_registration_workflow():

    analysis_info = {'do_fnirt': False,
                     'use_FS': False}

    wf = create_registration_workflow(analysis_info=analysis_info)
    wf.inputs.inputspec.EPI_space_file = op.join(test_data_path, 'sub-0020_gstroop_meanbold.nii.gz')
    wf.inputs.inputspec.output_directory = '/tmp/spynoza'
    wf.inputs.inputspec.T1_file = op.join(test_data_path, 'sub-0020_T1w.nii.gz')
    wf.inputs.inputspec.sub_id = 'sub-0020'
    wf.inputs.inputspec.standard_file = Info.standard_image('MNI152_T1_2mm_brain.nii.gz')
    wf.base_dir = '/tmp/spynoza/workingdir'
    wf = set_parameters_in_nodes(wf, flirt_e2t={'interp': 'trilinear'},
                                 flirt_t2s={'interp': 'trilinear'})
    wf.run()
