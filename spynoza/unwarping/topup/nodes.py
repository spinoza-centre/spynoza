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
