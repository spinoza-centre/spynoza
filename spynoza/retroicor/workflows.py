import nipype.pipeline as pe
from .nodes.pnm import PreparePNM, PNMtoEVs
from .nodes.utils import (_distill_slice_times_from_gradients,
                          _preprocess_nii_files_to_pnm_evs_prefix,
                          _slice_times_to_txt_file)
import nipype.interfaces.utility as niu


def create_retroicor_workflow(name = 'retroicor', order_or_timing = 'order'):
    
    """
    
    Creates RETROICOR regressors
    
    Example
    -------
    
    Inputs::
        inputnode.in_file - The .log file acquired together with EPI sequence
    Outputs::
        outputnode.regressor_files
    """
    
    # Define nodes:
    input_node = pe.Node(niu.IdentityInterface(fields=['in_files',
                                                    'phys_files',
                                                    'nr_dummies',
                                                    'MB_factor', 
                                                    'tr',
                                                    'slice_direction',
                                                    'phys_sample_rate',
                                                    'slice_timing',
                                                    'slice_order',
                                                    ]), name='inputspec')

    # the slice time preprocessing node before we go into popp (PreparePNM)
    slice_times_from_gradients = pe.MapNode(niu.Function(input_names=['in_file', 'phys_file', 'nr_dummies', 'MB_factor'], 
                        output_names=['out_file', 'fig_file'], 
                        function=_distill_slice_times_from_gradients), name='slice_times_from_gradients', iterfield = ['in_file','phys_file'])
    
    slice_times_to_txt_file = pe.Node(niu.Function(input_names=['slice_times'], 
                        output_names=['out_file'], 
                        function=_slice_times_to_txt_file), name='slice_times_to_txt_file')

    pnm_prefixer = pe.MapNode(niu.Function(input_names=['filename'], 
                        output_names=['out_string'], 
                        function=_preprocess_nii_files_to_pnm_evs_prefix), name='pnm_prefixer', iterfield = ['filename'])

    prepare_pnm = pe.MapNode(PreparePNM(), name='prepare_pnm', iterfield = ['in_file'])

    pnm_evs = pe.MapNode(PNMtoEVs(), name='pnm_evs', iterfield = ['functional_epi','cardiac','resp', 'prefix'])

    # Define output node
    output_node = pe.Node(niu.IdentityInterface(fields=['new_phys', 'fig_file', 'evs']), name='outputspec')

    ########################################################################################
    # workflow
    ########################################################################################

    retroicor_workflow = pe.Workflow(name=name)

    retroicor_workflow.connect(input_node, 'in_files', slice_times_from_gradients, 'in_file')
    retroicor_workflow.connect(input_node, 'phys_files', slice_times_from_gradients, 'phys_file')
    retroicor_workflow.connect(input_node, 'nr_dummies', slice_times_from_gradients, 'nr_dummies')
    retroicor_workflow.connect(input_node, 'MB_factor', slice_times_from_gradients, 'MB_factor')

    # conditional here, for the creation of a separate slice timing file if order_or_timing is 'timing'
    # order_or_timing can also be 'order'
    if order_or_timing ==   'timing':
        retroicor_workflow.connect(input_node, 'slice_timing', slice_times_to_txt_file, 'slice_times')

    retroicor_workflow.connect(input_node, 'phys_sample_rate', prepare_pnm, 'sampling_rate')
    retroicor_workflow.connect(input_node, 'tr', prepare_pnm, 'tr')

    retroicor_workflow.connect(slice_times_from_gradients, 'out_file', prepare_pnm, 'in_file')

    retroicor_workflow.connect(input_node, 'in_files', pnm_prefixer, 'filename')
    retroicor_workflow.connect(pnm_prefixer, 'out_string', pnm_evs, 'prefix')
    retroicor_workflow.connect(input_node, 'in_files', pnm_evs, 'functional_epi')
    retroicor_workflow.connect(input_node, 'slice_direction', pnm_evs, 'slice_dir')
    retroicor_workflow.connect(input_node, 'tr', pnm_evs, 'tr')

    # here the input to pnm_evs is conditional on order_or_timing again.
    if order_or_timing ==   'timing':
        retroicor_workflow.connect(slice_times_to_txt_file, 'out_file', pnm_evs, 'slice_timing')
    elif order_or_timing == 'order':
        retroicor_workflow.connect(input_node, 'slice_order', pnm_evs, 'slice_order')

    retroicor_workflow.connect(prepare_pnm, 'card', pnm_evs, 'cardiac')
    retroicor_workflow.connect(prepare_pnm, 'resp', pnm_evs, 'resp')

    retroicor_workflow.connect(slice_times_from_gradients, 'out_file', output_node, 'new_phys')
    retroicor_workflow.connect(slice_times_from_gradients, 'fig_file', output_node, 'fig_file')
    retroicor_workflow.connect(pnm_evs, 'evs', output_node, 'evs')


    
    return retroicor_workflow
