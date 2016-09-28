from __future__ import division, print_function

def fit_nuisances(in_file, regressor_list = []):
    """Performs a per-slice GLM on in_file, with per-TR regressors from regressor_list.
    Assumes slices to be the last spatial dimension of nii files.

    Parameters
    ----------
    in_file : str
        Absolute path to nifti-file.
    regressor_list : list
        list of absolute paths to per-slice regressor files

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

    func_nii = nib.load(in_file)
    dims = func_nii.shape
    affine = func_nii.affine

    func_data = func_nii.get_data()

    all_reg = np.zeros((len(regressor_list)+1,dims[-2],dims[-1]))
    # intercept
    all_reg[0,:,:] = 1
    # fill the regressor array from files
    for i in range(len(regressor_list)):
        all_reg[i+1] = nib.load(regressor_list[i]).get_data().squeeze()

    # data containers
    residual_data = np.zeros_like(func_data)
    rsq_data = np.zeros(list(dims[:-1]))
    beta_data = np.zeros(list(dims[:-1]) + [len(regressor_list)])

    # loop over slices
    for x in range(dims[-2]):
        slice_data = func_data[:,:,x,:].reshape((-1,dims[-1]))
        slice_regressors = all_reg[:,x,:]

        # fit
        betas, residuals_sum, rank, sse = LA.lstsq()

        # predicted data, rsq and residuals
        prediction = np.dot(betas.astype(np.float32).T, slice_regressors.astype(np.float32))
        rsq = 1.0 - np.sum((prediction - slice_data)**2, axis = -1) / np.sum(slice_data.squeeze()**2, axis = -1)
        residuals = slice_data - prediction

        # reshape and save
        residual_data[:,:,x,:] = residuals.reshape((dims[0], dims[1], dims[-1]))
        rsq_data[:,:,x] = rsq.reshape((dims[0], dims[1]))
        beta_data[:,:,x,:] = betas.reshape((dims[0], dims[1],len(regressor_list)+1))


    # save files
    residual_img = nib.Nifti1Image(residual_data, affine)
    res_file = os.path.abspath(os.path.basename(in_file).split('.')[:-2][0] + '_res.nii.gz')
    nib.save(residual_img, res_file)
    
    rsq_img = nib.Nifti1Image(rsq_data, affine)
    rsq_file = os.path.abspath(os.path.basename(in_file).split('.')[:-2][0] + '_rsq.nii.gz')
    nib.save(rsq_img, rsq_file)

    beta_img = nib.Nifti1Image(beta_data, affine)
    beta_file = os.path.abspath(os.path.basename(in_file).split('.')[:-2][0] + '_betas.nii.gz')
    nib.save(beta_img, beta_file)

    # return paths
    return res_file, rsq_file, beta_file