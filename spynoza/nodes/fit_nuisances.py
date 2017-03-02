from __future__ import division, print_function

def fit_nuisances(in_file, slice_regressor_list = [], vol_regressors = '', num_components = 8, method = 'PCA'):
    """Performs a per-slice GLM on nifti-file in_file, 
    with per-slice regressors from slice_regressor_list of nifti files,
    and per-TR regressors from vol_regressors text file.
    Assumes slices to be the last spatial dimension of nifti files,
    and time to be the last.

    Parameters
    ----------
    in_file : str
        Absolute path to nifti-file.
    slice_regressor_list : list
        list of absolute paths to per-slice regressor nifti files
    vol_regressor_list : str
        absolute path to per-TR regressor text file

    Returns
    -------
    res_file : str
        Absolute path to nifti-file containing residuals after regression.
    rsq_file : str
        Absolute path to nifti-file containing rsq of regression.
    beta_file : str
        Absolute path to nifti-file containing betas from regression.

    """

    import nibabel as nib
    import numpy as np
    import numpy.linalg as LA
    import os
    from sklearn import decomposition
    from scipy.signal import savgol_filter

    func_nii = nib.load(in_file)
    dims = func_nii.shape
    affine = func_nii.affine

    # import data and convert nans to numbers
    func_data = np.nan_to_num(func_nii.get_data())

    all_slice_reg = np.zeros((len(slice_regressor_list)+1,dims[-2],dims[-1]))
    # intercept
    all_slice_reg[0,:,:] = 1
    # fill the regressor array from files
    for i in range(len(slice_regressor_list)):
        all_slice_reg[i+1] = nib.load(slice_regressor_list[i]).get_data().squeeze()

    if vol_regressors != '':
        all_TR_reg = np.loadtxt(vol_regressors)
        if all_TR_reg.shape[-1] != all_slice_reg.shape[-1]: # check for the right format
            all_TR_reg = all_TR_reg.T

    # data containers
    residual_data = np.zeros_like(func_data)
    rsq_data = np.zeros(list(dims[:-1]))
    if num_components == 0:
        if vol_regressors != '':
            beta_data = np.zeros(list(dims[:-1]) + [1 + len(slice_regressor_list) + all_TR_reg.shape[0]])
        else:
            beta_data = np.zeros(list(dims[:-1]) + [1 + len(slice_regressor_list)])
    else:
        beta_data = np.zeros(list(dims[:-1]) + [num_components])

    # loop over slices
    for x in range(dims[-2]):
        slice_data = func_data[:,:,x,:].reshape((-1,dims[-1]))
        all_regressors = all_slice_reg[:,x,:]
        if vol_regressors != '':
            all_regressors = np.vstack((all_regressors, all_TR_reg))
        all_regressors = np.nan_to_num(all_regressors)

        if num_components != 0:
            if method == 'PCA':
                pca = decomposition.PCA(n_components = num_components, whiten = True)
                all_regressors = pca.fit_transform(all_regressors.T).T
            elif method == 'ICA':
                ica = decomposition.FastICA(n_components = num_components, whiten = True)
                all_regressors = ica.fit_transform(all_regressors.T).T

        # fit
        betas, residuals_sum, rank, sse = LA.lstsq(all_regressors.T, slice_data.T)

        # predicted data, rsq and residuals
        prediction = np.dot(betas.T, all_regressors)
        rsq = 1.0 - np.sum((prediction - slice_data)**2, axis = -1) / np.sum(slice_data.squeeze()**2, axis = -1)
        residuals = slice_data - prediction

        # reshape and save
        residual_data[:,:,x,:] = residuals.reshape((dims[0], dims[1], dims[-1]))
        rsq_data[:,:,x] = rsq.reshape((dims[0], dims[1]))
        beta_data[:,:,x,:] = betas.T.reshape((dims[0], dims[1],all_regressors.shape[0]))

        print("slice %d finished nuisance GLM for %s"%(x, in_file))

    # save files
    residual_img = nib.Nifti1Image(np.nan_to_num(residual_data), affine)
    res_file = os.path.abspath(in_file[:-7]) + '_res.nii.gz'
    nib.save(residual_img, res_file)
    
    rsq_img = nib.Nifti1Image(np.nan_to_num(rsq_data), affine)
    rsq_file = os.path.abspath(in_file)[:-7] + '_rsq.nii.gz'
    nib.save(rsq_img, rsq_file)

    beta_img = nib.Nifti1Image(np.nan_to_num(beta_data), affine)
    beta_file = os.path.abspath(in_file)[:-7] + '_betas.nii.gz'
    nib.save(beta_img, beta_file)

    # return paths
    return res_file, rsq_file, beta_file