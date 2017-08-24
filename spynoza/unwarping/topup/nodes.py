import nipype.pipeline.engine as pe
import nipype.interfaces.utility as util

from nipype.interfaces.base import traits, File, BaseInterface, BaseInterfaceInputSpec, TraitedSpec
from niworkflows.common import report as nrc
from niworkflows import NIWORKFLOWS_LOG
from nilearn.masking import compute_epi_mask

import os


def get_topup_data(subject, task, run, data_dir='/data/sourcedata'):
    from bids.grabbids import BIDSLayout
    import nibabel as nb
    
    layout = BIDSLayout(data_dir)    
    bold = layout.get(subject=subject, task=task, run=run, type='bold')
    
    # Make sure there is only one nifti-file for this subject/task/run
    assert(len(bold) == 1)
    
    bold = bold[0].filename    
    fieldmap = layout.get_fieldmap(bold)
    
    # Make sure we are dealing with an EPI ('topup') fieldmap here
    assert(fieldmap['type'] == 'epi')    
    fieldmap = fieldmap['epi']
    
    bold_metadata = layout.get_metadata(bold)
    
    if 'NDynamics' not in bold_metadata:
        bold_metadata['NDynamics'] = nb.load(bold).shape[-1]
        
    fieldmap_metadata = layout.get_metadata(fieldmap)
    
    if 'NDynamics' not in fieldmap_metadata:
        fieldmap_metadata['NDynamics'] = nb.load(fieldmap).shape[-1]    
    
    return bold, bold_metadata, fieldmap, fieldmap_metadata

BIDSDataGrabber = util.Function(function=get_topup_data,
                                input_names=['subject',
                                             'task',
                                             'run'],
                                output_names=['bold',
                                              'bold_metadata',
                                              'fieldmap',
                                              'fieldmap_metadata'])



def topup_scan_params(bold_metadata, fieldmap_metadata, mode='concatenate'):
    import numpy as np
    import os
    
    n_bold_volumes = bold_metadata['NDynamics']
    n_epi_volumes = fieldmap_metadata['NDynamics']
    
    bold_total_readouttime = bold_metadata['TotalReadoutTime']
    epi_total_readouttime = fieldmap_metadata['TotalReadoutTime']
    
    bold_phaseEncodingDirection = bold_metadata['PhaseEncodingDirection']
    epi_phaseEncodingDirection = fieldmap_metadata['PhaseEncodingDirection']
    
    if type(bold_phaseEncodingDirection) is str:
        bold_phaseEncodingDirection = [bold_phaseEncodingDirection]
        
    if type(epi_phaseEncodingDirection) is str:
        epi_phaseEncodingDirection = [epi_phaseEncodingDirection]
    
    if mode == 'concatenate':
        bold_idx = n_bold_volumes
        scan_param_array = np.zeros((n_bold_volumes + n_epi_volumes, 4))
    elif mode == 'average':
        bold_idx = 1
        scan_param_array = np.zeros((2, 4))

    
    for encoding_direction in bold_phaseEncodingDirection:
        if encoding_direction.endswith('-'):
            scan_param_array[:bold_idx, ['i', 'j', 'k'].index(encoding_direction[0])] = -1
        else:
            scan_param_array[:bold_idx, ['i', 'j', 'k'].index(encoding_direction[0])] = 1
            
    for encoding_direction in epi_phaseEncodingDirection:
        if encoding_direction.endswith('-'):
            scan_param_array[bold_idx:, ['i', 'j', 'k'].index(encoding_direction[0])] = -1
        else:
            scan_param_array[bold_idx:, ['i', 'j', 'k'].index(encoding_direction[0])] = 1
            
    
    # Vectors should be unity length
    scan_param_array[:, :3] /= np.sqrt((scan_param_array[:, :3]**2).sum(1))[:, np.newaxis]
    
    scan_param_array[:bold_idx, 3] = bold_total_readouttime
    scan_param_array[bold_idx:, 3] = epi_total_readouttime
                

    fn = os.path.abspath('scan_params.txt')
    
    np.savetxt(fn, scan_param_array, fmt='%1.6f')
    
    return fn


TopupScanParameters = util.Function(function=topup_scan_params,
                                    input_names=['mode',
                                                 'bold_metadata',
                                                 'fieldmap_metadata'],
                                    output_names=['encoding_file'])


class ComputeEPIMaskInputSpec(nrc.ReportCapableInputSpec,
                              BaseInterfaceInputSpec):
    in_file = File(exists=True, desc="3D or 4D EPI file")
    lower_cutoff = traits.Float(0.2, desc='lower cutoff', usedefault=True)
    upper_cutoff = traits.Float(0.85, desc='upper cutoff', usedefault=True)


class ComputeEPIMaskOutputSpec(nrc.ReportCapableOutputSpec):
    mask_file = File(exists=True, desc="Binary brain mask")


class ComputeEPIMask(nrc.SegmentationRC, BaseInterface):
    input_spec = ComputeEPIMaskInputSpec
    output_spec = ComputeEPIMaskOutputSpec

    def _run_interface(self, runtime):
        mask_nii = compute_epi_mask(self.inputs.in_file, lower_cutoff=self.inputs.lower_cutoff, upper_cutoff=self.inputs.upper_cutoff)
        mask_nii.to_filename("mask_file.nii.gz")

        self._mask_file = os.path.abspath("mask_file.nii.gz")

        runtime.returncode = 0
        return super(ComputeEPIMask, self)._run_interface(runtime)

    def _list_outputs(self):
        outputs = super(ComputeEPIMask, self)._list_outputs()
        outputs['mask_file'] = self._mask_file
        return outputs

    def _post_run_hook(self, runtime):
        ''' generates a report showing slices from each axis of an arbitrary
        volume of in_file, with the resulting binary brain mask overlaid '''

        self._anat_file = self.inputs.in_file
        self._mask_file = self.aggregate_outputs().mask_file
        self._seg_files = [self._mask_file]
        self._masked = True
        self._report_title = "nilearn.compute_epi_mask: brain mask over EPI input"

        NIWORKFLOWS_LOG.info('Generating report for nilearn.compute_epi_mask. file "%s", and mask file "%s"',
                             self._anat_file, self._mask_file)


class CopyHeaderInputSpec(BaseInterfaceInputSpec):
    in_file = File(exists=True, mandatory=True, desc='the file we get the data from')
    hdr_file = File(exists=True, mandatory=True, desc='the file we get the header from')


class CopyHeaderOutputSpec(TraitedSpec):
    out_file = File(exists=True, desc='written file path')


class CopyHeader(BaseInterface):
    """
    Copy a header from the `hdr_file` to `out_file` with data drawn from
    `in_file`.
    """
    input_spec = CopyHeaderInputSpec
    output_spec = CopyHeaderOutputSpec

    def _run_interface(self, runtime):
        in_img = nb.load(self.inputs.hdr_file)
        out_img = nb.load(self.inputs.in_file)
        new_img = out_img.__class__(out_img.get_data(), in_img.affine, in_img.header)
        new_img.set_data_dtype(out_img.get_data_dtype())

        out_name = fname_presuffix(self.inputs.in_file,
                                   suffix='_fixhdr', newpath='.')
        new_img.to_filename(out_name)
        self._results['out_file'] = out_name
        return runtime
