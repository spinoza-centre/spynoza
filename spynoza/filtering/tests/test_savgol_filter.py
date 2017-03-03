from spynoza.filtering import Savgol_filter
import nipype.pipeline as pe
import os.path as op

func_data = op.join(op.dirname(op.dirname(op.dirname(__file__))),
                    'data', 'test_data', 'func_brain.nii.gz')

def test_savgol_filter_node():

    sg_node = pe.Node(interface=Savgol_filter, name='savgol_filt')
    sg_node.inputs.in_file = func_data
    res = sg_node.run()
    assert(op.isfile(res.outputs.out_file))
