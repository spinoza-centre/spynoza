from nipype.interfaces.fsl import Info
from spynoza.registration.workflows import create_registration_workflow
import os.path as op

test_dir = op.join(op.dirname(op.dirname(op.dirname(__file__))),
                   'data', 'test_data')


def test_registration_workflow():

    analysis_info = {'do_fnirt': False,
                     'use_FS': False}

    wf = create_registration_workflow(analysis_info=analysis_info)
    wf.inputs.inputspec.EPI_space_file = op.join(test_dir, 'session_EPI_space.nii.gz')
    wf.inputs.inputspec.output_directory = '/tmp/spynoza'
    wf.inputs.inputspec.T1_file = op.join(test_dir, 'highres.nii.gz')
    wf.inputs.inputspec.sub_id = 'sub-001'
    wf.inputs.inputspec.standard_file = Info.standard_image('MNI152_T1_2mm_brain.nii.gz')
    wf.base_dir = '/tmp/spynoza/out'
    wf.run()

if __name__ == '__main__':

    test_registration_workflow()