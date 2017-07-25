import nipype.pipeline as pe
import nipype.interfaces.fsl.preprocess as fsl
from nipype.interfaces.utility import IdentityInterface
from .nodes import (Prepare_phasediff, Radials_per_second, Dilate_mask,
                    Compute_echo_spacing, Make_output_filename)

def create_B0_workflow(name ='b0_unwarping', compute_echo_spacing=True):
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
                                                             'echo_spacing',
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
    unwarp_workflow.connect(input_node, 'in_files', out_file, 'in_file')
    unwarp_workflow.connect(input_node, 'fieldmap_pha', norm_pha, 'in_file')
    unwarp_workflow.connect(input_node, 'fieldmap_mag', mask_mag, 'in_file')
    unwarp_workflow.connect(mask_mag, 'mask_file', mask_mag_dil, 'in_file')
    unwarp_workflow.connect(input_node, 'fieldmap_mag', prelude, 'magnitude_file')
    unwarp_workflow.connect(norm_pha, 'out_file', prelude, 'phase_file')
    unwarp_workflow.connect(mask_mag_dil, 'out_file', prelude, 'mask_file')
    unwarp_workflow.connect(prelude, 'unwrapped_phase_file', radials_per_second, 'in_file')
    unwarp_workflow.connect(input_node, 'te_diff', radials_per_second, 'asym')
    unwarp_workflow.connect(mask_mag, 'out_file', registration, 'in_file')
    unwarp_workflow.connect(input_node, 'in_files', registration, 'reference')
    unwarp_workflow.connect(radials_per_second, 'out_file', applyxfm, 'in_file')
    unwarp_workflow.connect(registration, 'out_matrix_file', applyxfm, 'in_matrix_file')
    unwarp_workflow.connect(input_node, 'in_files', applyxfm, 'reference')
    if compute_echo_spacing:
        unwarp_workflow.connect(input_node, 'wfs', echo_spacing, 'wfs')
        unwarp_workflow.connect(input_node, 'epi_factor', echo_spacing, 'epi_factor')
        unwarp_workflow.connect(input_node, 'acceleration', echo_spacing, 'acceleration')
        unwarp_workflow.connect(echo_spacing, 'echo_spacing', fugue, 'dwell_time')
    else:
        unwarp_workflow.connect(input_node, 'echo_spacing', fugue, 'dwell_time')
    unwarp_workflow.connect(input_node, 'in_files', fugue, 'in_file')
    unwarp_workflow.connect(out_file, 'out_file', fugue, 'unwarped_file')
    unwarp_workflow.connect(applyxfm, 'out_file', fugue, 'fmap_in_file')
    unwarp_workflow.connect(input_node, 'te_diff', fugue, 'asym_se_time')
    unwarp_workflow.connect(input_node, 'phase_encoding_direction', fugue, 'unwarp_direction')
    unwarp_workflow.connect(fugue, 'unwarped_file', outputnode, 'out_files')
    unwarp_workflow.connect(applyxfm, 'out_file', outputnode, 'field_coefs')
    
    return unwarp_workflow
