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

def _compute_echo_spacing(wfs, etl, acceleration):
    return ((1000.0 * wfs)/(434.215 * (etl+1))/acceleration) / 1000.0

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
    
def create_unwarping_workflow(name = 'unwarp',):
    
    """
    
    Does B0 field unwarping
    
    Example
    -------
    >>> nipype_epicorrect = create_epidewarp_pipeline('nipype_epidewarp', fieldmap_registration=False)
    >>> nipype_epicorrect.inputs.inputnode.in_file - The volume acquired with EPI sequence
    >>> nipype_epicorrect.inputs.inputnode.fieldmap_mag - The magnitude of the fieldmap
    >>> nipype_epicorrect.inputs.inputnode.fieldmap_pha - The phase difference of the fieldmap
    >>> nipype_epicorrect.inputs.inputnode.wfs - The water-fat-shift
    >>> nipype_epicorrect.inputs.inputnode.etl - ??
    >>> nipype_epicorrect.inputs.inputnode.acceleration - Acceleration factor used for EPI parallel imaging (GRAPPA)
    >>> nipype_epicorrect.inputs.inputnode.te_diff' - Time difference between TE in seconds.
    >>> nipype_epicorrect.inputs.inputnode.unwarp_direction
    >>> nipype_epicorrect.run()
    
    Inputs::
        inputnode.in_file - The volume acquired with EPI sequence
        inputnode.fieldmap_mag - The magnitude of the fieldmap
        inputnode.fieldmap_pha - The phase difference of the fieldmap
        inputnode.wfs - The water-fat-shift
        inputnode.etl - ??
        inputnode.acceleration - Acceleration factor used for EPI parallel imaging (GRAPPA)
        inputnode.te_diff' - Time difference between TE in seconds.
        inputnode.unwarp_direction
    Outputs::
        outputnode.epi_corrected
    """
    
    # Define input and workflow:
    inputnode = pe.Node(niu.IdentityInterface(fields=['in_file',
                                                    'fieldmap_mag',
                                                    'fieldmap_pha',
                                                    'wfs', 
                                                    'etl', 
                                                    'acceleration', 
                                                    'te_diff', 
                                                    'unwarp_direction'
                                                    ]), name='inputnode')
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
    registration = pe.Node(fsl.FLIRT(bins=256, cost='corratio', dof=6, interp='trilinear',  searchr_x=[-10, 10], searchr_y=[-10, 10], searchr_z=[-10, 10]), name='registration')
   
    # transform unwrapped fieldmap (rad/s)
    applyxfm = pe.Node(fsl.ApplyXfm(interp='trilinear'), name='apply_xfm')
    
    # compute effective echospacing:
    echo_spacing = pe.Node(niu.Function(input_names=['wfs', 'etl', 'acceleration'], output_names=['out_file'], function=_compute_echo_spacing), name='echo_spacing')
    
    # Unwarp with FSL Fugue
    fugue = pe.Node(fsl.FUGUE(unwarp_direction='y', median_2dfilter=True), name='fugue')
    
    # Define output node
    outputnode = pe.Node(niu.IdentityInterface(fields=['epi_corrected']), name='outputnode')
    
    # Connect
    unwarp_workflow.connect([
                    (inputnode,             norm_pha, [('fieldmap_pha', 'in_file')])
                    ,(inputnode,            mask_mag, [('fieldmap_mag', 'in_file')])
                    ,(mask_mag,             mask_mag_dil, [('mask_file', 'in_file')])
                    ,(inputnode,            prelude, [('fieldmap_mag', 'magnitude_file')])
                    ,(norm_pha,             prelude, [('out_file', 'phase_file')])
                    ,(mask_mag_dil,         prelude, [('out_file', 'mask_file')])
                    ,(prelude,              radials_per_second, [('unwrapped_phase_file', 'in_file')])
                    ,(inputnode,            radials_per_second, [('te_diff', 'asym')])
                    ,(mask_mag,             registration, [('out_file', 'in_file')])
                    ,(inputnode,            registration, [('in_file', 'reference')])
                    ,(radials_per_second,   applyxfm, [('out_file', 'in_file')])  
                    ,(registration,         applyxfm, [('out_matrix_file', 'in_matrix_file')]) 
                    ,(inputnode,            applyxfm, [('in_file', 'reference')])  
                    ,(inputnode,            echo_spacing, [('wfs', 'wfs')])
                    ,(inputnode,            echo_spacing, [('etl', 'etl')])  
                    ,(inputnode,            echo_spacing, [('acceleration', 'acceleration')])
                    ,(inputnode,            fugue, [('in_file', 'in_file')])
                    ,(inputnode,            fugue, [('in_file', 'unwarped_file')])  
                    ,(applyxfm,             fugue, [('out_file', 'fmap_in_file')])  
                    ,(echo_spacing,         fugue, [('out_file', 'dwell_time')])  
                    ,(inputnode,            fugue, [('te_diff', 'asym_se_time')])  
                    ,(fugue,                outputnode, [('unwarped_file', 'epi_corrected')])
                    ])
    
    return unwarp_workflow