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

from spynoza.workflows.all_7T import create_all_7T_workflow

# we will create a workflow from a BIDS formatted input, at first for the specific use case 
# of a 7T PRF experiment's preprocessing. 

FS_subject_dir = os.environ['SUBJECTS_DIR'] #'/Users/knapen/subjects/'

# # a project directory that we assume has already been created. 
# raw_data_dir = '/home/raw_data/PRF_7T/data/BIDSdata/'
# preprocessed_data_dir = '/home/shared/2016/visual/PRF_7T/'

# for testing on laptop:
# raw_data_dir = '/home/raw_data/PRF_7T/data/BIDSdata/'
raw_data_dir = '/Users/knapen/Documents/projects/spynoza/data/raw/'
preprocessed_data_dir = '/Users/knapen/Documents/projects/spynoza/data/preprocessed/'

# for when the subjects will be a numbered list
# subject_list = ['sub-' + str(x).zfill(3) for x in range(1,15)]

# for now, testing on a single subject, with appropriate FS ID, this will have to be masked.
present_subject, FS_ID = 'sub-NA', 'NA_220813_12'
opd = op.join(preprocessed_data_dir, present_subject)

# some settings, such as scan parameters, and analysis prescription
session_info = {'te': 0.025, 'pe_direction': 'y','epi_factor': 37, 'use_FS': True, 'do_fnirt': False}

if not op.isdir(preprocessed_data_dir):
    os.makedirs(preprocessed_data_dir)

# the actual workflow

all_7T_workflow = create_all_7T_workflow(session_info, name = 'all_7T')

all_7T_workflow.inputs.inputspec.raw_directory = raw_data_dir
all_7T_workflow.inputs.inputspec.present_subject = present_subject
all_7T_workflow.inputs.inputspec.run_nrs = range(1,6)
all_7T_workflow.inputs.inputspec.output_directory = opd

all_7T_workflow.inputs.inputspec.topup_conf_file = op.join(os.environ['FSL_DIR'], 'etc/flirtsch/b02b0-empty.cnf')

all_7T_workflow.inputs.inputspec.which_file_is_EPI_space = 'middle'

all_7T_workflow.inputs.inputspec.FS_ID = FS_ID
all_7T_workflow.inputs.inputspec.FS_subject_dir = FS_subject_dir
all_7T_workflow.inputs.inputspec.standard_file = op.join(os.environ['FSL_DIR'], 'data/standard/MNI152_T1_1mm_brain.nii.gz')

all_7T_workflow.inputs.inputspec.psc_func = 'median'


all_7T_workflow.run('MultiProc', plugin_args={'n_procs': 4})
