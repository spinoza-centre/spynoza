import os.path as op
import nipype.pipeline as pe
from nipype.interfaces import fsl
import nipype.interfaces.io as nio
from nipype.interfaces.utility import Function, Merge, IdentityInterface
from spynoza.nodes.utils import get_scaninfo

def create_topup_workflow(session_info, name='topup'):
    import os.path as op
    import nipype.pipeline as pe
    from nipype.interfaces import fsl
    from nipype.interfaces.utility import Function, Merge, IdentityInterface
    from spynoza.nodes.utils import get_scaninfo, dyns_min_1, topup_scan_params, apply_scan_params

    input_node = pe.Node(IdentityInterface(
        fields=['in_files', 'alt_files', 'conf_file', 'output_directory',
                'pe_direction', 'te', 'epi_factor']), name='inputspec')

    output_node = pe.Node(IdentityInterface(fields='out_files'), name='outputspec')

    get_info = pe.MapNode(Function(input_names='in_file', output_names=['TR', 'shape', 'dyns', 'voxsize', 'affine'],
                                function=get_scaninfo), name='get_scaninfo',
                    iterfield=['in_file'])

    dyns_min_1_node = pe.MapNode(Function(input_names='dyns', output_names='dyns_1',
                                       function=dyns_min_1), name='dyns_min_1_node',
                    iterfield=['dyns'])

    topup_scan_params_node = pe.Node(Function(input_names=['pe_direction', 'te', 'epi_factor'],
                                              output_names='fn',
                                              function=topup_scan_params),
                                     name='topup_scan_params')

    apply_scan_params_node = pe.MapNode(Function(input_names=['pe_direction', 'te', 'epi_factor', 'nr_trs'],
                                              output_names='fn',
                                              function=apply_scan_params),
                                     name='apply_scan_params',
                    iterfield=['nr_trs'])

    PE_ref = pe.MapNode(fsl.ExtractROI(t_size=1), name='PE_ref', iterfield = ['in_file', 't_min'])
    PE_alt = pe.MapNode(fsl.ExtractROI(t_min=0, t_size=1), name='PE_alt', iterfield = ['in_file']) # hard-coded the timepoint for this node, no more need for alt_t.
    PE_comb = pe.Node(Merge(2), name='PE_list')
    PE_merge = pe.Node(fsl.Merge(dimension='t'), name='PE_merged')

    # implementing the contents of b02b0.cnf in the args, 
    # while supplying an emtpy text file as a --config option 
    # gets topup going on our server. 
    topup_args = """--warpres=20,16,14,12,10,6,4,4,4 --subsamp=1,1,1,1,1,1,1,1,1 --fwhm=8,6,4,3,3,2,1,0,0 --miter=5,5,5,5,5,10,10,20,20 --lambda=0.005,0.001,0.0001,0.000015,0.000005,0.0000005,0.00000005,0.0000000005,0.00000000001 --ssqlambda=1 --regmod=bending_energy --estmov=1,1,1,1,1,0,0,0,0 --minmet=0,0,0,0,0,1,1,1,1 --splineorder=3 --numprec=double --interp=spline --scale=1 -v"""
    # topup_node = pe.MapNode(fsl.TOPUP(args = topup_args), name='topup', iterfield=['in_file'])
    topup_node = pe.MapNode(fsl.TOPUP(), name='topup', iterfield=['in_file'])
    unwarp = pe.MapNode(fsl.ApplyTOPUP(in_index=[1], method='jac'), name='unwarp', iterfield = ['in_file', 'in_topup_fieldcoef', 'in_topup_movpar', 'encoding_file'])

    ########################################################################################
    # WORKFLOW
    ########################################################################################
    topup_workflow = pe.Workflow(name=name)

    # add session info variables to input node
    input_node.inputs.te = session_info['te']
    input_node.inputs.pe_direction = session_info['pe_direction']
    input_node.inputs.epi_factor = session_info['epi_factor']

    # these are now mapnodes because they split up over files
    topup_workflow.connect(input_node, 'in_files', get_info, 'in_file')
    topup_workflow.connect(input_node, 'in_files', PE_ref, 'in_file')
    topup_workflow.connect(input_node, 'in_files', unwarp, 'in_file')
    topup_workflow.connect(input_node, 'alt_files', PE_alt, 'in_file')

    # this is a simple node, connecting to the input node
    topup_workflow.connect(input_node, 'pe_direction', topup_scan_params_node, 'pe_direction')
    topup_workflow.connect(input_node, 'te', topup_scan_params_node, 'te')
    topup_workflow.connect(input_node, 'epi_factor', topup_scan_params_node, 'epi_factor')

    # preparing a node here, which automatically iterates over dyns output of the get_info mapnode
    topup_workflow.connect(input_node, 'te', apply_scan_params_node, 'te')
    topup_workflow.connect(input_node, 'pe_direction', apply_scan_params_node, 'pe_direction')
    topup_workflow.connect(input_node, 'epi_factor', apply_scan_params_node, 'epi_factor')
    topup_workflow.connect(get_info, 'dyns', apply_scan_params_node, 'nr_trs')

    # the nr_trs and in_files both propagate into the PR_ref node
    topup_workflow.connect(get_info, 'dyns', dyns_min_1_node, 'dyns')
    topup_workflow.connect(dyns_min_1_node, 'dyns_1', PE_ref, 't_min')

    # and linking the encoding files, with the in_files and alt_files inputs
    topup_workflow.connect(topup_scan_params_node, 'fn', topup_node, 'encoding_file')
    topup_workflow.connect(apply_scan_params_node, 'fn', unwarp, 'encoding_file')

    topup_workflow.connect(PE_ref, 'roi_file', PE_comb, 'in1')
    topup_workflow.connect(PE_alt, 'roi_file', PE_comb, 'in2')
    topup_workflow.connect(PE_comb, 'out', PE_merge, 'in_files')
    topup_workflow.connect(PE_merge, 'merged_file', topup_node, 'in_file')
    topup_workflow.connect(input_node, 'conf_file', topup_node, 'config')
    topup_workflow.connect(topup_node, 'out_fieldcoef', unwarp, 'in_topup_fieldcoef')
    topup_workflow.connect(topup_node, 'out_movpar', unwarp, 'in_topup_movpar')

    topup_workflow.connect(unwarp, 'out_corrected', output_node, 'corrected_files')

    ########################################################################################
    # outputs via datasink
    ########################################################################################
    datasink = pe.Node(nio.DataSink(infields=['topup'], container = ''), name='sinker')

    # first link the workflow's output_directory into the datasink.
    topup_workflow.connect(input_node, 'output_directory', datasink, 'base_directory')
    # and the rest
    topup_workflow.connect(unwarp, 'out_corrected', datasink, 'topup')


    return topup_workflow
