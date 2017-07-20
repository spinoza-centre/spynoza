from __future__ import absolute_import
import os
import socket
import pytest
import shutil
import os.path as op
from nipype.interfaces.fsl import Info
from ..workflows import create_registration_workflow
from ... import test_data_path
from ...utils import set_parameters_in_nodes

test_data_path = op.join(test_data_path, 'sub-0020')


@pytest.fixture(scope="module", autouse=True)
def setup():
    print('Setup ...')
    yield None
    print('teardown ...')
    #shutil.rmtree(op.join('/tmp/spynoza/workingdir', 'reg'))

# Cannot get freesurfer installed on travis (wget stalls ...)
is_travis = 'TRAVIS' in os.environ
FS = [False] if is_travis else [True, False]

# Only test AFNI skullstrip if not on UvA desktop (weird GLX error)
hostname = socket.gethostname()
AFNI = [True, False] if hostname != 'uva' else [False]

@pytest.mark.parametrize('use_FS', FS)
@pytest.mark.parametrize('use_AFNI_ss', [False])
@pytest.mark.registration
def test_registration_workflow(use_FS, use_AFNI_ss):

    analysis_info = {'do_fnirt': False,
                     'use_FS': use_FS,
                     'do_FAST': False,
                     'use_AFNI_ss': use_AFNI_ss}

    wf = create_registration_workflow(analysis_info=analysis_info)
    wf.inputs.inputspec.EPI_space_file = op.join(test_data_path, 'func', 'sub-0020_task-harriri_meanbold.nii.gz')
    wf.inputs.inputspec.output_directory = '/tmp/spynoza'
    wf.inputs.inputspec.T1_file = op.join(test_data_path, 'anat', 'sub-0020_T1w.nii.gz')
    wf.inputs.inputspec.sub_id = 'sub-0020'
    wf.inputs.inputspec.standard_file = Info.standard_image('MNI152_T1_2mm_brain.nii.gz')
    wf.inputs.inputspec.freesurfer_subject_ID = 'sub-0020'
    wf.inputs.inputspec.freesurfer_subject_dir = op.join(op.dirname(test_data_path), 'fs')
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