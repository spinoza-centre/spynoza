from __future__ import absolute_import
import pytest
from ... import test_data_path
from ..nodes import Savgol_filter
import nipype.pipeline as pe
import os.path as op

func_data = [op.join(test_data_path, 'sub-0020', 'func', 'sub-0020_task-harriri_bold_cut.nii.gz'),
             op.join(test_data_path, 'sub-0020', 'func', 'sub-0020_task-wm_bold_cut.nii.gz')]


@pytest.mark.filtering
def test_savgol_filter_node():

    sg_node = pe.MapNode(interface=Savgol_filter, name='savgol_filt', iterfield=['in_file'])
    sg_node.inputs.in_file = func_data
    res = sg_node.run()

    for f in res.outputs.out_file:
        assert(op.isfile(f))