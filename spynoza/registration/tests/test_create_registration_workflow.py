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
    shutil.rmtree(op.join('/tmp/spynoza/workingdir', 'reg'))


@pytest.mark.parametrize('use_FS', [False, True])
@pytest.mark.registration
def test_registration_workflow(use_FS):

    analysis_info = {'do_fnirt': False,
                     'use_FS': use_FS,
                     'do_FAST': False}

    wf = create_registration_workflow(analysis_info=analysis_info)
    wf.inputs.inputspec.EPI_space_file = op.join(test_data_path, 'sub-0020_gstroop_meanbold.nii.gz')
    wf.inputs.inputspec.output_directory = '/tmp/spynoza'
    wf.inputs.inputspec.T1_file = op.join(test_data_path, 'sub-0020_T1w.nii.gz')
    wf.inputs.inputspec.sub_id = 'sub-0020'
    wf.inputs.inputspec.standard_file = Info.standard_image('MNI152_T1_2mm_brain.nii.gz')
    wf.inputs.inputspec.freesurfer_subject_ID = 'sub-0020'
    wf.inputs.inputspec.freesurfer_subject_dir = op.join(test_data_path, 'fs')
    wf.base_dir = '/tmp/spynoza/workingdir'

    # This is to speed up the analysis
    if not analysis_info['use_FS']:
        wf = set_parameters_in_nodes(wf, flirt_e2t={'interp': 'trilinear', 'cost_func': 'corratio'},
                                     flirt_t2s={'interp': 'trilinear'})

    wf.run()

    reg_files = ['example_func.nii.gz', 'example_func2highres.mat',
                 'example_func2standard.mat', 'highres.nii.gz',
                 'highres2example_func.mat', 'highres2standard.mat', 'standard.nii.gz',
                 'standard2example_func.mat', 'standard2highres.mat']

    datasink = wf.inputs.inputspec.output_directory = '/tmp/spynoza'
    for f in reg_files:
        f_path = op.join(datasink, 'sub-0020', 'reg', f)
        assert(op.isfile(f_path))