import nipype.pipeline.engine as pe
import nipype.interfaces.utility as util

from nipype.interfaces.base import traits, File, BaseInterface, BaseInterfaceInputSpec, TraitedSpec
from nilearn.masking import compute_epi_mask

import os



def topup_scan_params(bold_epi_metadata, epi_op_metadata, mode='concatenate'):
    import numpy as np
    import os
    
    bold_epi_total_readouttime = bold_epi_metadata['TotalReadoutTime']
    epi_op_total_readouttime = epi_op_metadata['TotalReadoutTime']
    
    bold_epi_phaseEncodingDirection = bold_epi_metadata['PhaseEncodingDirection']
    epi_phaseEncodingDirection = epi_op_metadata['PhaseEncodingDirection']
    
    if type(bold_epi_phaseEncodingDirection) is str:
        bold_epi_phaseEncodingDirection = [bold_phaseEncodingDirection]
        
    if type(epi_phaseEncodingDirection) is str:
        epi_phaseEncodingDirection = [epi_phaseEncodingDirection]
    
    if mode == 'concatenate':
        raise NotImplementedError()
    elif mode == 'average':
        bold_epi_idx = 1
        scan_param_array = np.zeros((2, 4))

    
    for encoding_direction in bold_epi_phaseEncodingDirection:
        if encoding_direction.endswith('-'):
            scan_param_array[:bold_epi_idx, ['i', 'j', 'k'].index(encoding_direction[0])] = -1
        else:
            scan_param_array[:bold_epi_idx, ['i', 'j', 'k'].index(encoding_direction[0])] = 1
            
    for encoding_direction in epi_phaseEncodingDirection:
        if encoding_direction.endswith('-'):
            scan_param_array[bold_epi_idx:, ['i', 'j', 'k'].index(encoding_direction[0])] = -1
        else:
            scan_param_array[bold_epi_idx:, ['i', 'j', 'k'].index(encoding_direction[0])] = 1
            
    
    # Vectors should be unity length
    scan_param_array[:, :3] /= np.sqrt((scan_param_array[:, :3]**2).sum(1))[:, np.newaxis]
    
    scan_param_array[:bold_epi_idx, 3] = bold_epi_total_readouttime
    scan_param_array[bold_epi_idx:, 3] = epi_op_total_readouttime
                

    fn = os.path.abspath('scan_params.txt')
    
    np.savetxt(fn, scan_param_array, fmt='%1.6f')
    
    return fn


TopupScanParameters = util.Function(function=topup_scan_params,
                                    input_names=['mode',
                                                 'bold_epi_metadata',
                                                 'epi_op_metadata'],
                                    output_names=['encoding_file'])




# Monkey patch nipype
from nipype.interfaces.afni.preprocess import Qwarp, QwarpInputSpec, QwarpOutputSpec
class QwarpPlusMinusInputSpec(QwarpInputSpec):
    in_file = File(
        desc='Source image (opposite phase encoding direction than base image)',
        argstr='-source %s',
        mandatory=True,
        exists=True,
        copyfile=False)
    source_file = File(
        desc='Source image (opposite phase encoding direction than base image)',
        argstr='-source %s',
        exists=True,
        deprecated='1.1.2',
        new_name='in_file',
        copyfile=False)
    out_file = File(
        argstr='-prefix %s',
        value='Qwarp.nii.gz',
        position=0,
        usedefault=True,
        desc="Output file")
    plusminus = traits.Bool(
        True,
        usedefault=True,
        position=1,
        desc='Normally, the warp displacements dis(x) are defined to match'
        'base(x) to source(x+dis(x)).  With this option, the match'
        'is between base(x-dis(x)) and source(x+dis(x)) -- the two'
        'images \'meet in the middle\'. For more info, view Qwarp` interface',
        argstr='-plusminus',
        xor=['duplo', 'allsave', 'iwarp'])


class QwarpPlusMinusOutputSpec(QwarpOutputSpec):
    warped_source = File(desc='Undistorted source file.', exists=True)
    warped_base = File(desc='Undistorted base file.', exists=True)
    source_warp = File(
        desc="Field suceptibility correction warp (in 'mm') for source image.",
        exists=True)
    base_warp = File(
        desc="Field suceptibility correction warp (in 'mm') for base image.",
        exists=True)


class QwarpPlusMinus(Qwarp):
    """A version of 3dQwarp for performing field susceptibility correction
    using two images with opposing phase encoding directions.
    For complete details, see the `3dQwarp Documentation.
    <https://afni.nimh.nih.gov/pub/dist/doc/program_help/3dQwarp.html>`_
    Examples
    ========
    >>> from nipype.interfaces import afni
    >>> qwarp = afni.QwarpPlusMinus()
    >>> qwarp.inputs.source_file = 'sub-01_dir-LR_epi.nii.gz'
    >>> qwarp.inputs.nopadWARP = True
    >>> qwarp.inputs.base_file = 'sub-01_dir-RL_epi.nii.gz'
    >>> qwarp.cmdline
    '3dQwarp -prefix Qwarp.nii.gz -plusminus -base sub-01_dir-RL_epi.nii.gz -nopadWARP -source sub-01_dir-LR_epi.nii.gz'
    >>> res = warp.run()  # doctest: +SKIP
    """

    input_spec = QwarpPlusMinusInputSpec
    output_spec = QwarpPlusMinusOutputSpec

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs['warped_source'] = os.path.abspath("Qwarp_PLUS.nii.gz")
        outputs['warped_base'] = os.path.abspath("Qwarp_MINUS.nii.gz")
        outputs['source_warp'] = os.path.abspath("Qwarp_PLUS_WARP.nii.gz")
        outputs['base_warp'] = os.path.abspath("Qwarp_MINUS_WARP.nii.gz")

        return outputs
