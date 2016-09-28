# from nipype import config
# config.enable_debug_mode()
# Importing necessary packages
import os
import os.path as op
import glob
import json
import nipype
import matplotlib.pyplot as plt
import nipype.interfaces.fsl as fsl
import nipype.pipeline.engine as pe
import nipype.interfaces.utility as util
import nipype.interfaces.io as nio
import nibabel as nib
from IPython.display import Image
from nipype.interfaces.utility import Function, Merge, IdentityInterface
from nipype.interfaces.io import SelectFiles, DataSink
from IPython.display import Image

from IPython import embed as shell


from spynoza.workflows.all_7T import create_all_7T_workflow

# we will create a workflow from a BIDS formatted input, at first for the specific use case 
# of a 7T PRF experiment's preprocessing. 

FS_subject_dir = os.environ['SUBJECTS_DIR'] 

# a project directory that we assume has already been created. 
raw_data_dir = '/home/raw_data/PRF_7T/data/BIDSdata/'
preprocessed_data_dir = '/home/shared/2016/visual/PRF_7T/test/'

# for now, testing on a single subject, with appropriate FS ID, this will have to be masked.
sub_id, FS_ID = 'sub-NA', 'NA_220813_12'
opd = op.join(preprocessed_data_dir, sub_id)

# load the sequence parameters from json file
with open(os.path.join(raw_data_dir, 'multiband_prf_7T_acq.json')) as f:
    json_s = f.read()
    sequence_parameters = json.loads(json_s)

# some settings, such as scan parameters, and analysis prescription, mostly taken from json in raw file folder
session_info = {'te': sequence_parameters['EchoTime'], 
                'pe_direction': sequence_parameters['PhaseEncodingDirection'],
                'slice_direction': sequence_parameters['SliceDirection'],
                'epi_factor': sequence_parameters['EpiFactor'], 
                'slice_timing': sequence_parameters['SliceTiming'], 
                'slice_order': sequence_parameters['SliceOrder'], 
                'tr': sequence_parameters['RepetitionTime'], 
                'MB_factor': sequence_parameters['MultiBandFactor'], 
                'nr_dummies': sequence_parameters['NumberDummyScans'], 
                'phys_sample_rate': sequence_parameters['PhysiologySampleRate'], 
                'retroicor_order_or_timing': 'timing',    # can also be 'order' for non-MB sequences
                'use_FS': True, 
                'do_fnirt': False, 
                'bet_frac': 0.3, 
                'bet_vert_grad': 0.0}

if not op.isdir(preprocessed_data_dir):
    os.makedirs(preprocessed_data_dir)

# the actual workflow
all_7T_workflow = create_all_7T_workflow(session_info, name = 'all_7T')

# standard output variables
all_7T_workflow.inputs.inputspec.raw_directory = raw_data_dir
all_7T_workflow.inputs.inputspec.sub_id = sub_id
all_7T_workflow.inputs.inputspec.output_directory = opd

# the config file for topup
all_7T_workflow.inputs.inputspec.topup_conf_file = op.join(os.environ['FSL_DIR'], 'etc/flirtsch/b02b0.cnf')

# to what file do we motion correct?
all_7T_workflow.inputs.inputspec.which_file_is_EPI_space = 'middle'

# registration details
all_7T_workflow.inputs.inputspec.FS_ID = FS_ID
all_7T_workflow.inputs.inputspec.FS_subject_dir = FS_subject_dir
all_7T_workflow.inputs.inputspec.standard_file = op.join(os.environ['FSL_DIR'], 'data/standard/MNI152_T1_1mm_brain.nii.gz')

# percent signal change and average-across-runs settings
all_7T_workflow.inputs.inputspec.psc_func = 'median'
all_7T_workflow.inputs.inputspec.av_func = 'median'

# all the input variables for retroicor functionality
# the key 'retroicor_order_or_timing' determines whether slice timing
# or order is used for regressor creation
all_7T_workflow.inputs.inputspec.MB_factor = session_info['MB_factor']
all_7T_workflow.inputs.inputspec.nr_dummies = session_info['nr_dummies']
all_7T_workflow.inputs.inputspec.tr = session_info['tr']
all_7T_workflow.inputs.inputspec.slice_direction = session_info['slice_direction']
all_7T_workflow.inputs.inputspec.phys_sample_rate = session_info['phys_sample_rate']
all_7T_workflow.inputs.inputspec.slice_timing = session_info['slice_timing']
all_7T_workflow.inputs.inputspec.slice_order = session_info['slice_order']

# write out the graph and run
all_7T_workflow.write_graph(os.path.join(preprocessed_data_dir,'7T'))
all_7T_workflow.run('MultiProc', plugin_args={'n_procs': 8})
