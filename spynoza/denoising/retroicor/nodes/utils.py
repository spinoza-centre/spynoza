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

def _distill_slice_times_from_gradients(in_file, phys_file, nr_dummies, MB_factor=1, sample_rate=496):
    import os
    import numpy as np
    import pandas as pd
    import nibabel as nib
    import matplotlib.pyplot as plt
    
    # output:
    name, fext = os.path.splitext(os.path.basename(in_file))
    out_file = os.path.abspath('./%s_new.log' % name)
    fig_file = os.path.abspath('./%s_fig.png' % name)    
    
    # load nifti and attributes:
    nifti = nib.load(in_file)
    nr_slices = int(nifti.header.get_data_shape()[2] / MB_factor)
    nr_volumes = nifti.header.get_data_shape()[3]
    tr = float(nifti.header['pixdim'][4])
    
    # load physio data:
    phys = np.loadtxt(phys_file, skiprows=5)
    
    # compute gradient signal as sum x y z, and z-score:
    gradients = [6,7,8]
    gradient_signal = np.array([phys[:,g] for g in gradients]).sum(axis=0)
    gradient_signal = (gradient_signal-gradient_signal.mean()) / gradient_signal.std()
    
    # threshold:
    time_window_start = int(gradient_signal.shape[0]/2.0)
    time_window_end = int(time_window_start + (10 * tr * sample_rate))
    threshold = 5
    loop = True
    while loop:
        threshold -= 0.1
        if (gradient_signal[time_window_start:time_window_end]>threshold).sum() > (10 * nr_slices * 1.25):
            loop = False
    
    # slice time indexes:
    x = np.arange(gradient_signal.shape[0])
    slice_times = x[np.r_[False, np.array(np.diff(np.array(gradient_signal>threshold, dtype=int))==1, dtype=bool)]]
    
    # check if we had a double (due to shape gradient signal):
    if slice_times.shape[0] > (nr_volumes*nr_slices*2):
        slice_times = slice_times[0::2]
    
    # identify gap between shimming and dummies:
    gap = np.where(np.diff(slice_times) > ((nr_volumes / float(nr_slices))*10.0))[0][-1]
        
    # dummy slices and volumes:
    dummy_slice_indices = (np.arange(slice_times.shape[0]) > gap) * (np.arange(slice_times.shape[0]) < gap + (nr_dummies * nr_slices))
    dummy_slices = np.arange(slice_times.shape[0])[dummy_slice_indices]
    dummy_volumes = dummy_slices[0::nr_slices]

    # scans slices and volumes:
    scan_slice_indices = (np.arange(slice_times.shape[0]) > dummy_slices[-1])
    scan_slices = np.arange(slice_times.shape[0])[scan_slice_indices][0:(nr_volumes*nr_slices)]
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
    np.savetxt(out_file, phys_new, fmt=str('%3.2f'), delimiter='\t')
    
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
