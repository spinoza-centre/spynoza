# All credits to the fmriprep peeps
from nipype.interfaces.utility import Function

def erode_mask(in_file, epi_mask, epi_mask_erosion_mm=0,
                                erosion_mm=0):
    import os
    import nibabel as nib
    import scipy.ndimage as nd

    # thresholding
    probability_map_nii = nib.load(in_file)
    probability_map_data = probability_map_nii.get_data()
    probability_map_data[probability_map_data < 0.95] = 0
    probability_map_data[probability_map_data != 0] = 1

    epi_mask_nii = nib.load(epi_mask)
    epi_mask_data = epi_mask_nii.get_data()
    if epi_mask_erosion_mm:
        iters = int(epi_mask_erosion_mm/max(probability_map_nii.header.get_zooms()))
        epi_mask_data = nd.binary_erosion(epi_mask_data,
                                      iterations=iters).astype(int)
        eroded_mask_file = os.path.abspath("erodd_mask.nii.gz")
        niimg = nib.Nifti1Image(epi_mask_data, epi_mask_nii.affine, epi_mask_nii.header)
        niimg.to_filename(eroded_mask_file)
    else:
        eroded_mask_file = epi_mask

    probability_map_data[epi_mask_data != 1] = 0

    # shrinking
    if erosion_mm:
        iter_n = int(erosion_mm/max(probability_map_nii.header.get_zooms()))
        probability_map_data = nd.binary_erosion(probability_map_data,
                                                 iterations=iter_n).astype(int)

    new_nii = nib.Nifti1Image(probability_map_data, probability_map_nii.affine,
                             probability_map_nii.header)
    new_nii.to_filename("roi.nii.gz")
    return os.path.abspath("roi.nii.gz"), eroded_mask_file


Erode_mask = Function(function=erode_mask, input_names=['in_file',
                                                        'epi_mask',
                                                        'epi_mask_erosion_mm',
                                                        'erosion_mm'],
                      output_names=['roi_eroded', 'epi_mask_eroded'])


def combine_rois(in_CSF, in_WM, epi_ref):
    import os
    import numpy as np
    import nibabel as nib

    CSF_nii = nib.load(in_CSF)
    CSF_data = CSF_nii.get_data()

    WM_nii = nib.load(in_WM)
    WM_data = WM_nii.get_data()

    combined = np.zeros_like(WM_data)

    combined[WM_data != 0] = 1
    combined[CSF_data != 0] = 1

    epi_ref_nii = nib.load(epi_ref)
    affine, header = epi_ref_nii.affine, epi_ref_nii.header
    # we have to do this explicitly because of potential differences in
    # qform_code between the two files that prevent aCompCor to work
    new_nii = nib.Nifti1Image(combined, affine, header)
    new_nii.to_filename("logical_or.nii.gz")
    return os.path.abspath("logical_or.nii.gz")


Combine_rois = Function(function=combine_rois, input_names=['in_CSF', 'in_WM',
                                                            'epi_ref'],
                        output_names=['combined_roi'])


def combine_component_files(acomp, tcomp):
    import os.path as op
    import pandas as pd
    acomp_df = pd.read_csv(acomp, sep=str('\t'))
    tcomp_df = pd.read_csv(tcomp, sep=str('\t'))
    df = pd.concat((acomp_df, tcomp_df), axis=1)
    fn = op.abspath('all_compcor.tsv')
    df.to_csv(fn, index=None, sep=str('\t'))

    return fn

Combine_component_files = Function(function=combine_component_files,
                                   input_names=['acomp', 'tcomp'],
                                   output_names=['out_file'])