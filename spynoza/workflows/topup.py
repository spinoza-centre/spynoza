import nipype.pipeline as pe
from nipype.interfaces import fsl
from nipype.interfaces.utility import Function, Merge, IdentityInterface
from spynoza.nodes.utils import get_scaninfo
#from spynoza.nodes import topup_scan_params, apply_scan_params

input_node = pe.Node(IdentityInterface(
    fields=['in_file', 'alt_file', 'in_t', 'alt_t', 'scan_params', 'conf_file', 'apply_scan_params']),
    name='inputnode')

output_node = pe.Node(IdentityInterface(
    fields='out_file'), name='outputnode')

get_tr = pe.Node(Function(input_names='in_file', output_names=['TR', 'shape', 'dyns', 'voxsize', 'affine'],
                          function=get_scaninfo), name='get_scaninfo')
PE_ref = pe.Node(fsl.ExtractROI(t_size=1), name='PE_ref')
PE_alt = pe.Node(fsl.ExtractROI(t_size=1), name='PE_alt')
PE_comb = pe.Node(Merge(2), name='PE_list')
PE_merge = pe.Node(fsl.Merge(dimension='t'), name='PE_merged')
topup_node = pe.Node(fsl.TOPUP(), name='topup')
unwarp = pe.Node(fsl.ApplyTOPUP(in_index=[1], method='jac'), name='unwarp')

topup_workflow = pe.Workflow(name='topup')
topup_workflow.connect(input_node, 'in_file', PE_ref, 'in_file')
topup_workflow.connect(input_node, 'in_t', PE_ref, 't_min')
topup_workflow.connect(input_node, 'alt_file', PE_alt, 'in_file')
topup_workflow.connect(input_node, 'alt_t', PE_alt, 't_min')

topup_workflow.connect(input_node, 'scan_params', topup_node, 'encoding_file')
topup_workflow.connect(input_node, 'conf_file', topup_node, 'config')
topup_workflow.connect(input_node, 'in_file', unwarp, 'in_files')
topup_workflow.connect(input_node, 'apply_scan_params', unwarp, 'encoding_file')

topup_workflow.connect(PE_ref, 'roi_file', PE_comb, 'in1')
topup_workflow.connect(PE_alt, 'roi_file', PE_comb, 'in2')
topup_workflow.connect(PE_comb, 'out', PE_merge, 'in_files')
topup_workflow.connect(PE_merge, 'merged_file', topup_node, 'in_file')
topup_workflow.connect(topup_node, 'out_fieldcoef', unwarp, 'in_topup_fieldcoef')
topup_workflow.connect(topup_node, 'out_movpar', unwarp, 'in_topup_movpar')

if __name__ == '__main__':

    topup_workflow.write_graph()