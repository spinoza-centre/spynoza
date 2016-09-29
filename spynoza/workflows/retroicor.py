import os.path as op
import json
import nipype.pipeline as pe
import nipype.interfaces.fsl as fsl
import nipype.interfaces.utility as util
import nipype.interfaces.io as nio
from nipype.interfaces.utility import Function, IdentityInterface
from .sub_workflows import *
from ..nodes.fsl_retroicor import *
import nipype.interfaces.utility as niu

"""
TODO: remove some imports on top
"""

def _slice_times_to_txt_file(slice_times):
    import os
    import numpy as np

    # output:
    out_file = os.path.abspath('slice_times.txt')

    if type(slice_times) == list:
        np.savetxt(out_file, slice_times)

    return out_file

def _preprocess_nii_files_to_pnm_evs_prefix(filename):
    import os

    # take file name and cut off the .nii.gz part, add identifier
    out_string = filename[:-7] + '_pnm_regressors_'

    return out_string

def _distill_slice_times_from_gradients(in_file, phys_file, nr_dummies, MB_factor = 1):
    import os
    import numpy as np
    import nibabel as nib
    import matplotlib.pyplot as plt
    
    from IPython import embed as shell
    
    # sample rate:
    sample_rate = 496
    
    # output:
    name, fext = os.path.splitext(os.path.basename(in_file))
    out_file = os.path.abspath('./%s_new.log' % name)
    fig_file = os.path.abspath('./%s_fig.png' % name)    
    
    # load nifti and attributes:
    nifti = nib.load(in_file)
    nr_slices = nifti.header.get_data_shape()[2] / MB_factor
    nr_volumes = nifti.header.get_data_shape()[3]

    # load physio data:
    phys = np.loadtxt(phys_file, skiprows=5)
    
    # compute gradient signal as sum x y z, and z-score:
    gradients = [6,7,8]
    gradient_signal = np.array([phys[:,g] for g in gradients]).sum(axis = 0)
    gradient_signal = (gradient_signal-gradient_signal.mean()) / gradient_signal.std()
    
    # threshold:
    threshold = 5
    loop = True
    while loop:
        threshold -= 0.1
        if (gradient_signal>threshold).sum() > (nr_volumes * nr_slices * 1.1):
            loop = False
    
    # slice time indexes:
    x = np.arange(gradient_signal.shape[0])
    slice_times = x[np.array(np.diff(np.array(gradient_signal>threshold, dtype=int))==1, dtype=bool)]+1

    # check if we had a double (due to shape gradient signal):
    if slice_times.shape[0] > (nr_volumes*nr_slices*2):
        slice_times = slice_times[0::2]
    
    # identify gap between shimming and dummies:
    gap = np.where(np.diff(slice_times) > ((nr_volumes / float(nr_slices))*10.0))[0][-1]
    
    # dummy slices and volumes:
    dummy_slice_indices = (np.arange(slice_times.shape[0]) > gap) * (np.arange(slice_times.shape[0]) < gap + (nr_dummies * nr_slices))
    dummy_slices = np.arange(x.shape[0])[dummy_slice_indices]
    dummy_volumes = dummy_slices[0::nr_slices]

    # scans slices and volumes:
    scan_slice_indices = (np.arange(slice_times.shape[0]) > dummy_slices[-1])
    scan_slices = np.arange(x.shape[0])[scan_slice_indices][0:(nr_volumes*nr_slices)]
    scan_volumes = scan_slices[0:(nr_volumes*nr_slices):nr_slices]

    # append to physio file:
    scan_slices_timecourse = np.zeros(x.shape[0])
    scan_slices_timecourse[slice_times[scan_slices]] = 1
    scan_volumes_timecourse = np.zeros(x.shape[0])
    scan_volumes_timecourse[slice_times[scan_volumes]] = 1
    dummies_volumes_timecourse = np.zeros(x.shape[0])
    dummies_volumes_timecourse[slice_times[dummy_volumes]] = 1
    
    # output new physio file:
    phys_new = np.hstack((np.asmatrix(phys[:,4]).T, np.asmatrix(phys[:,5]).T, np.asmatrix(scan_slices_timecourse).T, np.asmatrix(scan_volumes_timecourse).T))
    np.savetxt(out_file, phys_new, fmt='%3.2f', delimiter='\t')
    
    # generate a list of figures:
    plot_timewindow = [np.arange(0, slice_times[dummy_volumes[-1]]+(4*sample_rate)),
                       np.arange(x.shape[0]-(8*sample_rate), x.shape[0]),]
    f = plt.figure(figsize = (15,6))                
    for i, times in enumerate(plot_timewindow):
        s = f.add_subplot(2,1,i+1)
        plt.plot(x[times], gradient_signal[times], label='summed gradient signal (x, y, z)')
        plt.plot(x[times], dummies_volumes_timecourse[times]*threshold*1.5, 'k', lw=3, label='dummies')
        plt.plot(x[times], scan_volumes_timecourse[times]*threshold*1.5, 'g', lw=3, label='triggers')
        plt.axhline(threshold, color='r', ls='--', label='threshold')
        s.set_title('summed gradient signal (x, y, z) -- nr volumes = {}'.format(sum(scan_volumes_timecourse)))
        s.set_xlabel('samples, {}Hz'.format(sample_rate))
        plt.ylim((0,threshold*1.5))
        plt.legend(loc=2)
    plt.tight_layout()
    f.savefig(fig_file)
    
    return out_file, fig_file

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