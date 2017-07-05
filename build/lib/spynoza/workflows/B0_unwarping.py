import os.path as op
import json
import nipype.pipeline as pe
import nipype.interfaces.fsl as fsl
import nipype.interfaces.utility as util
import nipype.interfaces.io as nio
from nipype.interfaces.utility import Function, IdentityInterface
from .sub_workflows import *
import nipype.interfaces.utility as niu

"""
TODO: remove some imports on top
"""

def _output_filename(in_file):
    import os
    return os.path.basename(in_file).split('.')[:-2][0] + '_B0.nii.gz'

def _compute_echo_spacing(wfs, epi_factor, acceleration):
    return ((1000.0 * wfs)/(434.215 * epi_factor)/acceleration) / 1000.0

def _prepare_phasediff(in_file):
    import nibabel as nib
    import os
    import numpy as np
    img = nib.load(in_file)
    max_diff = np.max(img.get_data().reshape(-1))
    min_diff = np.min(img.get_data().reshape(-1))
    A = (2.0 * np.pi)/(max_diff-min_diff)
    B = np.pi - (A * max_diff)
    diff_norm = img.get_data() * A + B
    
    name, fext = os.path.splitext(os.path.basename(in_file))
    if fext == '.gz':
        name, _ = os.path.splitext(name)
    out_file = os.path.abspath('./%s_2pi.nii.gz' % name)
    nib.save(nib.Nifti1Image(
        diff_norm, img.get_affine(), img.get_header()), out_file)
    return out_file

def _radials_per_second(in_file, asym):
    import nibabel as nib
    import os
    import numpy as np
    
    img = nib.load(in_file)
    img.data = img.get_data() * (1.0/asym)
    name, fext = os.path.splitext(os.path.basename(in_file))
    if fext == '.gz':
        name, _ = os.path.splitext(name)
    out_file = os.path.abspath('./%s_radials_ps.nii.gz' % name)
    nib.save(nib.Nifti1Image(img.data, img.get_affine(), img.get_header()), out_file)
    return out_file

def _dilate_mask(in_file, iterations=4):
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
    
def create_B0_workflow(name = 'unwarp',):
    
    """
    
    Does B0 field unwarping
    
    Example
    -------
    >>> nipype_epicorrect = create_unwarping_workflow('unwarp',)
    >>> unwarp.inputs.input_node.in_file = 'subj1_run1_bold.nii.gz'
    >>> unwarp.inputs.input_node.fieldmap_mag = 'subj1_run1_mag.nii.gz'
    >>> unwarp.inputs.input_node.fieldmap_pha = 'subj1_run1_phas.nii.gz'
    >>> unwarp.inputs.input_node.wfs = 12.223
    >>> unwarp.inputs.input_node.epi_factor = 35.0
    >>> unwarp.inputs.input_node.acceleration = 3.0
    >>> unwarp.inputs.input_node.te_diff = 0.005
    >>> unwarp.inputs.input_node.phase_encoding_direction = 'y'
    >>> nipype_epicorrect.run()
    
    Inputs::
        input_node.in_file - Volume acquired with EPI sequence
        input_node.fieldmap_mag - Magnitude of the fieldmap
        input_node.fieldmap_pha - Phase difference of the fieldmap
        input_node.wfs - Water-fat-shift in pixels
        input_node.epi_factor - EPI factor
        input_node.acceleration - Acceleration factor used for EPI parallel imaging (SENSE)
        input_node.te_diff - Time difference between TE in seconds.
        input_node.phase_encoding_direction - Unwarp direction (default should be "y")
    Outputs::
        outputnode.epi_corrected
    """
    
    # Define input and workflow:
    input_node = pe.Node(niu.IdentityInterface(fields=['in_files',
                                                    'fieldmap_mag',
                                                    'fieldmap_pha',
                                                    'wfs', 
                                                    'epi_factor', 
                                                    'acceleration', 
                                                    'te_diff', 
                                                    'phase_encoding_direction'
                                                    ]), name='inputspec')

    input_node.inputs.phase_encoding_direction = 'y'
    unwarp_workflow = pe.Workflow(name=name)
    
    # Normalize phase difference of the fieldmap phase to be [-pi, pi)
    norm_pha = pe.Node(niu.Function(input_names=['in_file'], output_names=['out_file'], function=_prepare_phasediff), name='normalize_phasediff')
    
    # Mask the magnitude of the fieldmap
    mask_mag = pe.Node(fsl.BET(mask=True), name='mask_magnitude')
    mask_mag_dil = pe.Node(niu.Function(input_names=['in_file'], output_names=['out_file'], function=_dilate_mask), name='mask_dilate')
    
    # Unwrap fieldmap phase using FSL PRELUDE
    prelude = pe.Node(fsl.PRELUDE(process3d=True), name='phase_unwrap')
    
    # Convert unwrapped fieldmap phase to radials per second:
    radials_per_second = pe.Node(niu.Function(input_names=['in_file', 'asym'], output_names=['out_file'], function=_radials_per_second), name='radials_ps')
    
    # Register unwrapped fieldmap (rad/s) to epi, using the magnitude of the fieldmap
    registration = pe.MapNode(fsl.FLIRT(bins=256, cost='corratio', dof=6, interp='trilinear',  searchr_x=[-10, 10], searchr_y=[-10, 10], searchr_z=[-10, 10]), iterfield=['reference'], name='registration')
   
    # transform unwrapped fieldmap (rad/s)
    applyxfm = pe.MapNode(fsl.ApplyXfm(interp='trilinear'), iterfield=['reference', 'in_matrix_file'], name='apply_xfm')
    
    # compute effective echospacing:
    echo_spacing = pe.Node(niu.Function(input_names=['wfs', 'epi_factor', 'acceleration'], output_names=['out_file'], function=_compute_echo_spacing), name='echo_spacing')
    
    # Unwarp with FSL Fugue
    fugue = pe.MapNode(fsl.FUGUE(median_2dfilter=True), iterfield=['in_file', 'unwarped_file', 'fmap_in_file'], name='fugue')
    
    # Convert unwrapped fieldmap phase to radials per second:
    out_file = pe.MapNode(niu.Function(input_names=['in_file',], output_names=['out_file'], function=_output_filename), iterfield=['in_file'], name='out_file')
    
    # Define output node
    outputnode = pe.Node(niu.IdentityInterface(fields=['out_files', 'field_coefs']), name='outputspec')
    
    # Connect
    unwarp_workflow.connect([
                    (input_node,             out_file, [('in_files', 'in_file')])
                    ,(input_node,            norm_pha, [('fieldmap_pha', 'in_file')])
                    ,(input_node,            mask_mag, [('fieldmap_mag', 'in_file')])
                    ,(mask_mag,             mask_mag_dil, [('mask_file', 'in_file')])
                    ,(input_node,            prelude, [('fieldmap_mag', 'magnitude_file')])
                    ,(norm_pha,             prelude, [('out_file', 'phase_file')])
                    ,(mask_mag_dil,         prelude, [('out_file', 'mask_file')])
                    ,(prelude,              radials_per_second, [('unwrapped_phase_file', 'in_file')])
                    ,(input_node,            radials_per_second, [('te_diff', 'asym')])
                    ,(mask_mag,             registration, [('out_file', 'in_file')])
                    ,(input_node,            registration, [('in_files', 'reference')])
                    ,(radials_per_second,   applyxfm, [('out_file', 'in_file')])  
                    ,(registration,         applyxfm, [('out_matrix_file', 'in_matrix_file')]) 
                    ,(input_node,            applyxfm, [('in_files', 'reference')])  
                    ,(input_node,            echo_spacing, [('wfs', 'wfs')])
                    ,(input_node,            echo_spacing, [('epi_factor', 'epi_factor')])  
                    ,(input_node,            echo_spacing, [('acceleration', 'acceleration')])
                    ,(input_node,            fugue, [('in_files', 'in_file')])
                    ,(out_file,             fugue, [('out_file', 'unwarped_file')])  
                    ,(applyxfm,             fugue, [('out_file', 'fmap_in_file')])  
                    ,(echo_spacing,         fugue, [('out_file', 'dwell_time')])  
                    ,(input_node,            fugue, [('te_diff', 'asym_se_time')])  
                    ,(input_node,            fugue, [('phase_encoding_direction', 'unwarp_direction')])  
                    ,(fugue,                outputnode, [('unwarped_file', 'out_files')])
                    ,(applyxfm,             outputnode, [('out_file', 'field_coefs')])  
                    ])
    
    return unwarp_workflow
