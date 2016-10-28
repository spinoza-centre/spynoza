from __future__ import division, print_function


def mask_nii_2_hdf5(in_files, mask_files, hdf5_file, folder_alias):
    """masks data in in_files with masks in mask_files,
    to be stored in an hdf5 file

    Takes a list of 4D fMRI nifti-files and masks the
    data with all masks in the list of nifti-files mask_files.
    These files are assumed to represent the same space, i.e.
    that of the functional acquisitions. 
    These are saved in hdf5_file, in the folder folder_alias.

    Parameters
    ----------
    in_files : list
        list of absolute path to functional nifti-files.
        all nifti files are assumed to have the same ndim
    mask_files : list
        list of absolute path to mask nifti-files.
        mask_files are assumed to be 3D
    hdf5_file : str
    	absolute path to hdf5 file.
   	folder_alias : str
   		name of the to-be-created folder in the hdf5 file.

    Returns
    -------
    hdf5_file : str
        absolute path to hdf5 file.
    """

    import nibabel as nib
    import os.path as op
    import numpy as np
    import tables

    success = True

    mask_data = [nib.load(mf).get_data() for mf in mask_files]
    nifti_data = [nib.load(nf).get_data() for nf in in_files]

    mask_names = [op.split(mf)[-1].split('.nii.gz')[0] for mf in mask_files]
    nifti_names = [op.split(mf)[-1].split('.nii.gz')[0] for nf in in_files]

    data = nib.load(in_files[0])
    dims = data.shape
    n_dims = data.ndim

    h5file = tables.open_file(hdf5_file, mode = "w", title = hdf5_file)
    # get or make group for alias folder
    try:
        folder_alias_run_group = h5file.get_node("/", name = folder_alias, classname='Group')
    except NoSuchNodeError:
        print('Adding group ' + folder_alias + ' to this file')
        folder_alias_run_group = h5file.create_group("/", folder_alias, folder_alias)

    for (roi, roi_name) in zip(mask_data, mask_names):
        # get or make group for alias/roi
        try:
            run_group = h5file.get_node(where = "/" + folder_alias, name = roi_name, classname='Group')
        except NoSuchNodeError:
            print('Adding group ' + folder_alias + '_' + roi_name + ' to this file')
            run_group = h5file.create_group("/" + folder_alias, roi_name, folder_alias + '_' + roi_name)
        
        for (nii_d, nii_name) in zip(nifti_data, nifti_names):
            if n_dims == 3:
                these_roi_data = nii_d[roi]
            elif n_dims == 4:   # timeseries data, last dimension is time.
                these_roi_data = nii_d[roi,:]
            else:
                print("n_dims in data {nifti} do not fit with mask".format(nii_name))
                success = False

            h5file.create_array(run_group, nii_name, these_roi_data, roi_name + ' data from ' + nii_name)

    h5file.close()

    return hdf5_file

def roi_data_from_hdf(data_types_wildcards, roi_name_wildcard, hdf5_file, folder_alias):
    """takes data_type data from masks stored in hdf5_file

    Takes a list of 4D fMRI nifti-files and masks the
    data with all masks in the list of nifti-files mask_files.
    These files are assumed to represent the same space, i.e.
    that of the functional acquisitions. 
    These are saved in hdf5_file, in the folder folder_alias.

    Parameters
    ----------
    data_types_wildcards : list
        list of data types to be loaded.
        correspond to nifti_names in mask_2_hdf5
    roi_name_wildcard : str
        wildcard for masks. 
        corresponds to mask_name in mask_2_hdf5.
    hdf5_file : str
        absolute path to hdf5 file.
    folder_alias : str
        name of the folder in the hdf5 file from which data
        should be loaded.

    Returns
    -------
    output_data : list
        list of numpy arrays corresponding to data_types and roi_name_wildcards
    """
    import tables
    import itertools

    h5file = tables.open_file(hdf5_file, mode = "r")

    try:
        folder_alias_run_group = h5file.get_node(where = '/', name = folder_alias, classname='Group')
    except NoSuchNodeError:
        # import actual data
        print('No group ' + folder_alias + ' in this file')
        return None


    all_roi_names = h5file.list_nodes(where = '/' + folder_alias, classname = 'Group')
    roi_names = [rn for rn in all_roi_names if roi_name_wildcard in rn]
    if len(roi_names) == 0:
        print('No rois corresponding to ' + roi_wildcard + ' in group ' + folder_alias)
        return None
    
    data_arrays = []
    for rn in roi_names:
        try:
            roi_node = h5file.get_node(where = '/' + folder_alias, name = roi_name, classname='Group')
        except NoSuchNodeError:
            print('No data corresponding to ' + roi_name + ' in group ' + folder_alias)
            pass
        all_data_array_names = h5file.list_nodes(where = '/' + folder_alias + '/' + roi_name)
        data_array_names = [[dan for dan in all_data_array_names if dtwc in dan and dtwc + '_' not in dan] for dtwd in data_types_wildcards]
        data_array_names = list(itertools.chain(*data_array_names))
        
        if sort_data_types:
            data_array_names = sorted(data_array_names)

        if len(data_array_names) == 0:
            print('No data corresponding to ' + str(data_types_wildcards) + ' in group ' + folder_alias + '/' + rn)
            pass
        else:
            print('Taking data corresponding to ' + str(data_array_names) + ' from group ' + folder_alias + '/' + rn)
            data_arrays.append([])
            for dan in data_array_names:
                data_arrays[-1].append(eval('roi_node.' + dan + '.read()'))

    all_roi_data_np = np.hstack(all_roi_data).T

    return all_roi_data_np

