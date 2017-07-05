import nipype.pipeline as pe
import nipype.interfaces.fsl.preprocess as fsl
from nipype.interfaces.utility import IdentityInterface
from .nodes import (Prepare_phasediff, Radials_per_second, Dilate_mask,
                    Compute_echo_spacing, Make_output_filename)

def create_B0_workflow(name ='b0_unwarping'):
    """ Does B0 field unwarping
    
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
    input_node = pe.Node(name='inputspec',
                         interface=IdentityInterface(fields=['in_files',
                                                             'fieldmap_mag',
                                                             'fieldmap_pha',
                                                             'wfs',
                                                             'epi_factor',
                                                             'acceleration',
                                                             'te_diff',
                                                             'phase_encoding_direction']))
    unwarp_workflow = pe.Workflow(name=name)
    
    # Normalize phase difference of the fieldmap phase to be [-pi, pi)
    norm_pha = pe.Node(interface=Prepare_phasediff, name='normalize_phasediff')
    
    # Mask the magnitude of the fieldmap
    mask_mag = pe.Node(fsl.BET(mask=True), name='mask_magnitude')
    mask_mag_dil = pe.Node(interface=Dilate_mask, name='mask_dilate')
    
    # Unwrap fieldmap phase using FSL PRELUDE
    prelude = pe.Node(fsl.PRELUDE(process3d=True), name='phase_unwrap')
    
    # Convert unwrapped fieldmap phase to radials per second:
    radials_per_second = pe.Node(interface=Radials_per_second, name='radials_ps')
    
    # Register unwrapped fieldmap (rad/s) to epi, using the magnitude of the fieldmap
    registration = pe.MapNode(fsl.FLIRT(bins=256, cost='corratio', dof=6,
                                        interp='trilinear',
                                        searchr_x=[-10, 10],
                                        searchr_y=[-10, 10],
                                        searchr_z=[-10, 10]),
                              iterfield=['reference'],
                              name='registration')
   
    # transform unwrapped fieldmap (rad/s)
    applyxfm = pe.MapNode(fsl.ApplyXFM(interp='trilinear'),
                          iterfield=['reference', 'in_matrix_file'],
                          name='apply_xfm')
    
    # compute effective echospacing:
    echo_spacing = pe.Node(interface=Compute_echo_spacing, name='echo_spacing')
    
    # Unwarp with FSL Fugue
    fugue = pe.MapNode(interface=fsl.FUGUE(median_2dfilter=True),
                       iterfield=['in_file', 'unwarped_file', 'fmap_in_file'],
                       name='fugue')
    
    # Convert unwrapped fieldmap phase to radials per second:
    out_file = pe.MapNode(interface=Make_output_filename,
                          iterfield=['in_file'],
                          name='out_file')
    
    # Define output node
    outputnode = pe.Node(IdentityInterface(fields=['out_files', 'field_coefs']),
                         name='outputspec')
    
    # Connect
    unwarp_workflow.connect([
                    (input_node,              out_file, [('in_files', 'in_file')]),
                    (input_node,              norm_pha, [('fieldmap_pha', 'in_file')]),
                    (input_node,              mask_mag, [('fieldmap_mag', 'in_file')]),
                    (mask_mag,                mask_mag_dil, [('mask_file', 'in_file')]),
                    (input_node,              prelude, [('fieldmap_mag', 'magnitude_file')]),
                    (norm_pha,                prelude, [('out_file', 'phase_file')]),
                    (mask_mag_dil,            prelude, [('out_file', 'mask_file')]),
                    (prelude,                 radials_per_second, [('unwrapped_phase_file', 'in_file')]),
                    (input_node,              radials_per_second, [('te_diff', 'asym')]),
                    (mask_mag,                registration, [('out_file', 'in_file')]),
                    (input_node,              registration, [('in_files', 'reference')]),
                    (radials_per_second,      applyxfm, [('out_file', 'in_file')]),
                    (registration,            applyxfm, [('out_matrix_file', 'in_matrix_file')]),
                    (input_node,              applyxfm, [('in_files', 'reference')]),
                    (input_node,              echo_spacing, [('wfs', 'wfs')]),
                    (input_node,              echo_spacing, [('epi_factor', 'epi_factor')]),
                    (input_node,              echo_spacing, [('acceleration', 'acceleration')]),
                    (input_node,              fugue, [('in_files', 'in_file')]),
                    (out_file,                fugue, [('out_file', 'unwarped_file')]),
                    (applyxfm,                fugue, [('out_file', 'fmap_in_file')]),
                    (echo_spacing,            fugue, [('echo_spacing', 'dwell_time')]),
                    (input_node,              fugue, [('te_diff', 'asym_se_time')]),
                    (input_node,              fugue, [('phase_encoding_direction', 'unwarp_direction')]),
                    (fugue,                   outputnode, [('unwarped_file', 'out_files')]),
                    (applyxfm,                outputnode, [('out_file', 'field_coefs')])
                    ])
    
    return unwarp_workflow
