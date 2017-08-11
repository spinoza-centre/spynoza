import nipype.pipeline as pe
from nipype.interfaces import fsl
from ...utils import Get_scaninfo, Dyns_min_1
from nipype.interfaces.utility import Merge, IdentityInterface
from .nodes import Topup_scan_params, Apply_scan_params


def create_topup_workflow(analysis_info, name='topup'):

    ###########################################################################
    # NODES
    ###########################################################################

    input_node = pe.Node(IdentityInterface(
        fields=['in_files', 'alt_files', 'conf_file', 'output_directory',
                'echo_time', 'phase_encoding_direction', 'epi_factor']),
        name='inputspec')

    output_node = pe.Node(IdentityInterface(fields=['out_files', 'field_coefs']),
                          name='outputspec')

    get_info = pe.MapNode(interface=Get_scaninfo,
                          name='get_scaninfo',
                          iterfield=['in_file'])

    dyns_min_1_node = pe.MapNode(interface=Dyns_min_1,
                                 name='dyns_min_1_node',
                                 iterfield=['dyns'])

    topup_scan_params_node = pe.Node(interface=Topup_scan_params,
                                     name='topup_scan_params')

    apply_scan_params_node = pe.MapNode(interface=Apply_scan_params,
                                        name='apply_scan_params',
                                        iterfield=['nr_trs'])

    PE_ref = pe.MapNode(fsl.ExtractROI(t_size=1),
                        name='PE_ref',
                        iterfield=['in_file', 't_min'])

    # hard-coded the timepoint for this node, no more need for alt_t.
    PE_alt = pe.MapNode(fsl.ExtractROI(t_min=0, t_size=1),
                        name='PE_alt',
                        iterfield=['in_file'])

    PE_comb = pe.MapNode(Merge(2), name='PE_list', iterfield = ['in1', 'in2'])
    PE_merge = pe.MapNode(fsl.Merge(dimension='t'),
                          name='PE_merged',
                          iterfield=['in_files'])

    # implementing the contents of b02b0.cnf in the args, 
    # while supplying an emtpy text file as a --config option 
    # gets topup going on our server. 
    topup_args = """--warpres=20,16,14,12,10,6,4,4,4
    --subsamp=1,1,1,1,1,1,1,1,1
    --fwhm=8,6,4,3,3,2,1,0,0
    --miter=5,5,5,5,5,10,10,20,20
    --lambda=0.005,0.001,0.0001,0.000015,0.000005,0.0000005,0.00000005,0.0000000005,0.00000000001
    --ssqlambda=1
    --regmod=bending_energy
    --estmov=1,1,1,1,1,0,0,0,0
    --minmet=0,0,0,0,0,1,1,1,1
    --splineorder=3
    --numprec=double
    --interp=spline
    --scale=1 -v"""


    # Using newlines led to errors on Tux07
    topup_args = topup_args.replace('\n', ' ')

    topup_node = pe.MapNode(fsl.TOPUP(args=topup_args),
                            name='topup',
                            iterfield=['in_file'])
    unwarp = pe.MapNode(fsl.ApplyTOPUP(in_index=[1], method='jac'),
                        name='unwarp',
                        iterfield = ['in_files', 'in_topup_fieldcoef',
                                     'in_topup_movpar', 'encoding_file'])

    ###########################################################################
    # WORKFLOW
    ###########################################################################
    topup_workflow = pe.Workflow(name=name)

    # these are now mapnodes because they split up over files
    topup_workflow.connect(input_node, 'in_files', get_info, 'in_file')
    topup_workflow.connect(input_node, 'in_files', PE_ref, 'in_file')
    topup_workflow.connect(input_node, 'alt_files', PE_alt, 'in_file')

    # this is a simple node, connecting to the input node
    topup_workflow.connect(input_node, 'phase_encoding_direction', topup_scan_params_node, 'pe_direction')
    topup_workflow.connect(input_node, 'echo_time', topup_scan_params_node, 'te')
    topup_workflow.connect(input_node, 'epi_factor', topup_scan_params_node, 'epi_factor')

    # preparing a node here, which automatically iterates over dyns output of the get_info mapnode
    topup_workflow.connect(input_node, 'echo_time', apply_scan_params_node, 'te')
    topup_workflow.connect(input_node, 'phase_encoding_direction', apply_scan_params_node, 'pe_direction')
    topup_workflow.connect(input_node, 'epi_factor', apply_scan_params_node, 'epi_factor')
    topup_workflow.connect(get_info, 'dyns', apply_scan_params_node, 'nr_trs')

    # the nr_trs and in_files both propagate into the PR_ref node
    topup_workflow.connect(get_info, 'dyns', dyns_min_1_node, 'dyns')
    topup_workflow.connect(dyns_min_1_node, 'dyns_1', PE_ref, 't_min')

    topup_workflow.connect(PE_ref, 'roi_file', PE_comb, 'in1')
    topup_workflow.connect(PE_alt, 'roi_file', PE_comb, 'in2')
    topup_workflow.connect(PE_comb, 'out', PE_merge, 'in_files')

    topup_workflow.connect(topup_scan_params_node, 'fn', topup_node, 'encoding_file')
    topup_workflow.connect(PE_merge, 'merged_file', topup_node, 'in_file')
    topup_workflow.connect(input_node, 'conf_file', topup_node, 'config')

    topup_workflow.connect(input_node, 'in_files', unwarp, 'in_files')
    topup_workflow.connect(apply_scan_params_node, 'fn', unwarp, 'encoding_file')
    topup_workflow.connect(topup_node, 'out_fieldcoef', unwarp, 'in_topup_fieldcoef')
    topup_workflow.connect(topup_node, 'out_movpar', unwarp, 'in_topup_movpar')

    topup_workflow.connect(unwarp, 'out_corrected', output_node, 'out_files')
    topup_workflow.connect(topup_node, 'out_fieldcoef', output_node, 'field_coefs')

    # ToDo: automatic datasink?

    return topup_workflow
