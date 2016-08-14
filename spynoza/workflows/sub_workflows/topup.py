import os.path as op
import nipype.pipeline as pe
from nipype.interfaces import fsl
from nipype.interfaces.utility import Function, Merge, IdentityInterface
from spynoza.nodes.utils import get_scaninfo

def dyns_min_1(dyns):
    dyns_1 = dyns - 1
    return dyns_1

def topup_scan_params(pe_direction='y', te=0.025, epi_factor=37):

    import numpy as np
    import os
    import tempfile

    scan_param_array = np.zeros((2, 4))
    scan_param_array[0, ['x', 'y', 'z'].index(pe_direction)] = 1
    scan_param_array[1, ['x', 'y', 'z'].index(pe_direction)] = -1
    scan_param_array[:, -1] = te * epi_factor

    fn = os.path.join(tempfile.gettempdir(), 'scan_params.txt')
    np.savetxt(fn, scan_param_array, fmt='%1.3f')
    return fn

def apply_scan_params(pe_direction='y', te=0.025, epi_factor=37, nr_trs=1):

    import numpy as np
    import os
    import tempfile

    scan_param_array = np.zeros((nr_trs, 4))
    scan_param_array[:, ['x', 'y', 'z'].index(pe_direction)] = 1
    scan_param_array[:, -1] = te * epi_factor

    fn = os.path.join(tempfile.gettempdir(), 'scan_params_apply.txt')
    np.savetxt(fn, scan_param_array, fmt='%1.3f')
    return fn

def create_topup_workflow(name='topup'):
    import os.path as op
    import nipype.pipeline as pe
    from nipype.interfaces import fsl
    from nipype.interfaces.utility import Function, Merge, IdentityInterface
    from spynoza.nodes.utils import get_scaninfo

    # if we wrap this into a MapNode(Function())
    # interface, shouldn't we accept direct arguments to this function?
    input_node = pe.Node(IdentityInterface(
        fields=['in_file', 'alt_file', 'alt_t', 'conf_file',
                'pe_direction', 'te', 'epi_factor']), name='inputspec')

    output_node = pe.Node(IdentityInterface(fields='out_file'), name='outputspec')

    get_info = pe.Node(Function(input_names='in_file', output_names=['TR', 'shape', 'dyns', 'voxsize', 'affine'],
                                function=get_scaninfo), name='get_scaninfo')

    dyns_min_1_node = pe.Node(Function(input_names='dyns', output_names='dyns_1',
                                       function=dyns_min_1), name='dyns_min_1_node')

    topup_scan_params_node = pe.Node(Function(input_names=['pe_direction', 'te', 'epi_factor'],
                                              output_names='fn',
                                              function=topup_scan_params),
                                     name='topup_scan_params')

    apply_scan_params_node = pe.Node(Function(input_names=['pe_direction', 'te', 'epi_factor', 'nr_trs'],
                                              output_names='fn',
                                              function=apply_scan_params),
                                     name='apply_scan_params')

    PE_ref = pe.Node(fsl.ExtractROI(t_size=1), name='PE_ref')
    PE_alt = pe.Node(fsl.ExtractROI(t_size=1), name='PE_alt')
    PE_comb = pe.Node(Merge(2), name='PE_list')
    PE_merge = pe.Node(fsl.Merge(dimension='t'), name='PE_merged')

    # implementing the contents of b02b0.cnf in the args, 
    # while supplying an emtpy text file as a --config option 
    # gets topup going on our server. 
    topup_node = pe.Node(fsl.TOPUP(args = """--warpres=20,16,14,12,10,6,4,4,4 \
        --subsamp=1,1,1,1,1,1,1,1,1 \
        --fwhm=8,6,4,3,3,2,1,0,0 \
        --miter=5,5,5,5,5,10,10,20,20 \
        --lambda=0.005,0.001,0.0001,0.000015,0.000005,0.0000005,0.00000005,0.0000000005,0.00000000001 \
        --ssqlambda=1 \
        --regmod=bending_energy \
        --estmov=1,1,1,1,1,0,0,0,0 \
        --minmet=0,0,0,0,0,1,1,1,1 \
        --splineorder=3 \
        --numprec=double \
        --interp=spline \
        --scale=1 -v"""), name='topup')
    unwarp = pe.Node(fsl.ApplyTOPUP(in_index=[1], method='jac'), name='unwarp')

    ### WORKFLOW
    topup_workflow = pe.Workflow(name=name)
    topup_workflow.connect(input_node, 'in_file', PE_ref, 'in_file')
    topup_workflow.connect(input_node, 'in_file', get_info, 'in_file')
    topup_workflow.connect(input_node, 'alt_file', PE_alt, 'in_file')
    topup_workflow.connect(input_node, 'alt_t', PE_alt, 't_min')
    topup_workflow.connect(input_node, 'in_file', unwarp, 'in_files')
    topup_workflow.connect(input_node, 'pe_direction', topup_scan_params_node, 'pe_direction')
    topup_workflow.connect(input_node, 'pe_direction', apply_scan_params_node, 'pe_direction')
    topup_workflow.connect(input_node, 'te', topup_scan_params_node, 'te')
    topup_workflow.connect(input_node, 'te', apply_scan_params_node, 'te')
    topup_workflow.connect(input_node, 'epi_factor', topup_scan_params_node, 'epi_factor')
    topup_workflow.connect(input_node, 'epi_factor', apply_scan_params_node, 'epi_factor')

    topup_workflow.connect(get_info, 'dyns', dyns_min_1_node, 'dyns')
    topup_workflow.connect(dyns_min_1_node, 'dyns_1', PE_ref, 't_min')
    topup_workflow.connect(get_info, 'dyns', apply_scan_params_node, 'nr_trs')
    topup_workflow.connect(topup_scan_params_node, 'fn', topup_node, 'encoding_file')
    topup_workflow.connect(apply_scan_params_node, 'fn', unwarp, 'encoding_file')

    topup_workflow.connect(PE_ref, 'roi_file', PE_comb, 'in1')
    topup_workflow.connect(PE_alt, 'roi_file', PE_comb, 'in2')
    topup_workflow.connect(PE_comb, 'out', PE_merge, 'in_files')
    topup_workflow.connect(PE_merge, 'merged_file', topup_node, 'in_file')
    topup_workflow.connect(input_node, 'conf_file', topup_node, 'config')
    topup_workflow.connect(topup_node, 'out_fieldcoef', unwarp, 'in_topup_fieldcoef')
    topup_workflow.connect(topup_node, 'out_movpar', unwarp, 'in_topup_movpar')

    topup_workflow.connect(unwarp, 'out_corrected', output_node, 'out_file')

    return topup_workflow
