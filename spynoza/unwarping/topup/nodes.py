import nipype.pipeline.engine as pe
import nipype.interfaces.utility as util

from nipype.interfaces.base import traits, File, BaseInterface, BaseInterfaceInputSpec, TraitedSpec
from niworkflows.common import report as nrc
from niworkflows import NIWORKFLOWS_LOG
from nilearn.masking import compute_epi_mask

import os



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
