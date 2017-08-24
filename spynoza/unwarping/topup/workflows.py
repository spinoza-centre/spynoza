from .nodes import TopupScanParameters
from ...io import BIDSGrabber
from ...utils import ComputeEPIMask, CopyHeader

import nipype.pipeline as pe
from nipype.interfaces import fsl
import nipype.interfaces.utility as util
import nipype.interfaces.io as nio

from nipype.interfaces import ants

def create_bids_topup_workflow(mode='average',
                               name='bids_topup_workflow', 
                               base_dir='/home/neuro/workflow_folders'):

    inputnode = pe.Node(util.IdentityInterface(fields=['bold',
                                                       'bold_metadata',
                                                       'fieldmap',
                                                       'fieldmap_metadata']),
                        name='inputnode')

    workflow = pe.Workflow(name=name, base_dir=base_dir)

    # Mask the BOLD and fieldmap using compute_epi_maks from nilearn ("Nichols method")
    create_bold_mask = pe.Node(ComputeEPIMask(upper_cutoff=0.8), name='create_bold_mask')
    create_fieldmap_mask = pe.Node(ComputeEPIMask(upper_cutoff=0.8), name='create_fieldmap_mask')

    workflow.connect(inputnode, 'bold', create_bold_mask, 'in_file') 
    workflow.connect(inputnode, 'fieldmap', create_fieldmap_mask, 'in_file') 

    applymask_bold = pe.Node(fsl.ApplyMask(), name="mask_bold")
    applymask_fieldmap = pe.Node(fsl.ApplyMask(), name="mask_fieldmap")

    workflow.connect(create_bold_mask, 'mask_file', applymask_bold, 'mask_file') 
    workflow.connect(inputnode, 'bold', applymask_bold, 'in_file') 

    workflow.connect(create_fieldmap_mask, 'mask_file', applymask_fieldmap, 'mask_file') 
    workflow.connect(inputnode, 'fieldmap', applymask_fieldmap, 'in_file') 

    # Create the parameter file that steers TOPUP
    topup_parameters = pe.Node(TopupScanParameters, name='topup_scanparameters')
    topup_parameters.inputs.mode = mode
    workflow.connect(inputnode, 'bold_metadata', topup_parameters, 'bold_metadata')
    workflow.connect(inputnode, 'fieldmap_metadata', topup_parameters, 'fieldmap_metadata')

    topup_node = pe.Node(fsl.TOPUP(args='-v'),
                            name='topup')

    workflow.connect(topup_parameters, 'encoding_file', topup_node, 'encoding_file')

    merge_list = pe.Node(util.Merge(2), name='merge_lists')

    if mode == 'concatenate':
        workflow.connect(applymask_bold, 'out_file', merge_list, 'in1') 
        workflow.connect(applymask_fieldmap, 'out_file', merge_list, 'in2') 


    elif mode == 'average':
        mc_bold = pe.Node(fsl.MCFLIRT(cost='normcorr',
                          interpolation='sinc',
                          mean_vol=True), name='mc_bold')

        meaner_bold = pe.Node(fsl.MeanImage(), name='meaner_bold')
        workflow.connect(applymask_bold, 'out_file', mc_bold, 'in_file')
        workflow.connect(mc_bold, 'out_file', meaner_bold, 'in_file')

        mc_fieldmap = pe.Node(fsl.MCFLIRT(cost='normcorr',
                          interpolation='sinc',
                          mean_vol=True), name='mc_fieldmap')

        workflow.connect(meaner_bold, 'out_file', mc_fieldmap, 'ref_file')
        workflow.connect(applymask_fieldmap, 'out_file', mc_fieldmap, 'in_file')

        meaner_fieldmap = pe.Node(fsl.MeanImage(), name='meaner_fieldmap')
        workflow.connect(mc_fieldmap, 'out_file', meaner_fieldmap, 'in_file')

        workflow.connect(meaner_bold, 'out_file', merge_list, 'in1')
        workflow.connect(meaner_fieldmap, 'out_file', merge_list, 'in2')

    merger = pe.Node(fsl.Merge(dimension='t'), name='merger')
    workflow.connect(merge_list, 'out', merger, 'in_files')
    workflow.connect(merger, 'merged_file', topup_node, 'in_file')

    outputnode = pe.Node(util.IdentityInterface(fields=['out_corrected',
                                                        'out_field',
                                                        'out_movpar']),
                         name='outputnode')


    # Make the warps compatbile with ANTS
    cphdr_warp = pe.Node(CopyHeader(), name='cphdr_warp')

    workflow.connect(topup_node, ('out_warps', _pick_first), cphdr_warp, 'in_file')
    workflow.connect(inputnode, 'bold', cphdr_warp, 'hdr_file')

    to_ants = pe.Node(util.Function(function=_add_dimension), name='to_ants')
    workflow.connect(cphdr_warp, 'out_file', to_ants, 'in_file')

    unwarp_reference = pe.Node(ants.ApplyTransforms(dimension=3,
                                                        float=True,
                                                        interpolation='LanczosWindowedSinc'),
                               name='unwarp_reference')

    if mode == 'concatenate':
        workflow.connect(applymask_bold, 'out_file', unwarp_reference, 'input_image')
    elif mode == 'average':
        workflow.connect(meaner_bold, 'out_file', unwarp_reference, 'input_image')

    workflow.connect(to_ants, 'out', unwarp_reference, 'transforms')
    workflow.connect(inputnode, 'bold', unwarp_reference, 'reference_image')

    # Write all interesting stuff to outputnode
    workflow.connect(topup_node, 'out_field', outputnode, 'out_field')
    workflow.connect(topup_node, 'out_warps', outputnode, 'out_warps')
    workflow.connect(to_ants, 'out', outputnode, 'out_warp')
    workflow.connect(unwarp_reference, 'output_image', outputnode, 'unwarped_image')

    return workflow

# Helper functions
# --------------------

def _add_dimension(in_file):
    import nibabel as nb
    import numpy as np
    import os

    nii = nb.load(in_file)
    hdr = nii.header.copy()
    hdr.set_data_dtype(np.dtype('<f4'))
    hdr.set_intent('vector', (), '')

    field = nii.get_data()
    field = field[:, :, :, np.newaxis, :]

    out_file = os.path.abspath("warpfield.nii.gz")

    nb.Nifti1Image(field.astype(np.dtype('<f4')), nii.affine, hdr).to_filename(out_file)

    return out_file


def _pick_first(l):
    return l[0]
