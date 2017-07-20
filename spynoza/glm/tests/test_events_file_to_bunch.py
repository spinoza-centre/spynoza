from __future__ import absolute_import
import os.path as op
import pytest
import nipype.pipeline as pe
from ..nodes import Events_file_to_bunch
from ... import test_data_path

test_data_path = op.join(test_data_path, 'sub-0020')


@pytest.mark.eventsfile2bunch
def test_create_modelgen_workflow():

    eventsfile2bunch = pe.MapNode(interface=Events_file_to_bunch,
                                  iterfield=['in_file'], name='eventsfile2bunch')

    eventsfile2bunch.base_dir = '/tmp/spynoza/workingdir'
    eventsfile2bunch.inputs.in_file = [op.join(test_data_path, 'func', 'sub-0020_task-harriri_events.tsv'),
                                       op.join(test_data_path, 'func', 'sub-0020_task-wm_events.tsv')]
    eventsfile2bunch.inputs.single_trial = False
    eventsfile2bunch.inputs.sort_by_onset = False
    eventsfile2bunch.inputs.exclude = None
    eventsfile2bunch.run()
