import pytest
from ... import test_data_path
from ..nodes import Savgol_filter
import nipype.pipeline as pe
import os.path as op

func_data = op.join(test_data_path, 'sub-0020_anticipation_cut.nii.gz')

@pytest.mark.filtering
def test_savgol_filter_node():

    sg_node = pe.Node(interface=Savgol_filter, name='savgol_filt')
    sg_node.inputs.in_file = func_data
    res = sg_node.run()
    assert(op.isfile(res.outputs.out_file))
