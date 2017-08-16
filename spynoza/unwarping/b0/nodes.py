from nipype.interfaces.utility import Function


def make_output_filename(in_file):
    import os.path as op
    return op.basename(in_file).split('.')[:-2][0] + '_B0.nii.gz'


Make_output_filename = Function(function=make_output_filename,
                                input_names=['in_file'],
                                output_names=['out_file'])


def compute_echo_spacing_philips(wfs, epi_factor, acceleration):
    return ((1000.0 * wfs) / (434.215 * epi_factor) / acceleration) / 1000.0


Compute_echo_spacing_philips = Function(function=compute_echo_spacing_philips,
                                input_names=['wfs', 'epi_factor', 'acceleration'],
                                output_names=['echo_spacing'])

def compute_echo_spacing_siemens(echo_spacing, acceleration):
    return echo_spacing / acceleration


Compute_echo_spacing_siemens = Function(function=compute_echo_spacing_siemens,
                                input_names=['echo_spacing', 'acceleration'],
                                output_names=['echo_spacing'])

def te_diff_ms(te_diff):
    return te_diff * 1000.0

TE_diff_ms = Function(function=te_diff_ms,
                                input_names=['te_diff'],
                                output_names=['te_diff'])

def prepare_phasediff(in_file):
    import nibabel as nib
    import os
    import numpy as np
    img = nib.load(in_file)
    max_diff = np.max(img.get_data().reshape(-1))
    min_diff = np.min(img.get_data().reshape(-1))
    A = (2.0 * np.pi) / (max_diff - min_diff)
    B = np.pi - (A * max_diff)
    diff_norm = img.get_data() * A + B

    name, fext = os.path.splitext(os.path.basename(in_file))
    if fext == '.gz':
        name, _ = os.path.splitext(name)
    out_file = os.path.abspath('./%s_2pi.nii.gz' % name)
    nib.save(nib.Nifti1Image(
        diff_norm, img.get_affine(), img.get_header()), out_file)
    return out_file


Prepare_phasediff = Function(function=prepare_phasediff,
                             input_names=['in_file'],
                             output_names=['out_file'])


def radials_per_second(in_file, asym):
    import nibabel as nib
    import os

    img = nib.load(in_file)
    img.data = img.get_data() * (1.0 / asym)
    name, fext = os.path.splitext(os.path.basename(in_file))
    if fext == '.gz':
        name, _ = os.path.splitext(name)
    out_file = os.path.abspath('./%s_radials_ps.nii.gz' % name)
    nib.save(nib.Nifti1Image(img.data, img.get_affine(), img.get_header()),
             out_file)
    return out_file


Radials_per_second = Function(function=radials_per_second,
                              input_names=['in_file', 'asym'],
                              output_names=['out_file'])


def dilate_mask(in_file, iterations=4):
    import nibabel as nib
    import scipy.ndimage as ndimage
    import os

    img = nib.load(in_file)
    img.data = ndimage.binary_dilation(img.get_data(), iterations=iterations)
    name, fext = os.path.splitext(os.path.basename(in_file))
    if fext == '.gz':
        name, _ = os.path.splitext(name)
    out_file = os.path.abspath('./%s_dil.nii.gz' % name)
    nib.save(img, out_file)
    return out_file


Dilate_mask = Function(function=dilate_mask,
                       input_names=['in_file', 'iterations'],
                       output_names=['out_file'])
