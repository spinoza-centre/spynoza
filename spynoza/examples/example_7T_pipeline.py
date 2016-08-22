from nipype import config
config.enable_debug_mode()
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

# Importing of custom nodes from spynoza packages; assumes that spynoza is installed:
# pip install git+https://github.com/spinoza-centre/spynoza.git@master
from spynoza.nodes import apply_sg_filter, get_scaninfo
from spynoza.workflows.topup import create_topup_workflow
from spynoza.workflows.motion_correction import create_motion_correction_workflow
from spynoza.workflows.registration import create_registration_workflow

# we will create a workflow from a BIDS formatted input, at first for the specific use case 
# of a 7T PRF experiment's preprocessing. 

# # a project directory that we assume has already been created. 
# preprocessed_data_dir = '/home/shared/2016/visual/PRF_7T/'
# # raw_data_dir = '/home/raw_data/PRF_7T/data/BIDSdata/'
# raw_data_dir = '/home/raw_data/PRF_7T/data/BIDSdata/'

# a project directory that we assume has already been created. 
preprocessed_data_dir = '/Users/knapen/Documents/projects/spynoza/data/preprocessed/'
# raw_data_dir = '/home/raw_data/PRF_7T/data/BIDSdata/'
raw_data_dir = '/Users/knapen/Documents/projects/spynoza/data/raw/'
FS_subject_dir = '/Users/knapen/subjects/'

# for when the subjects will be a numbered list
# subject_list = ['sub-' + str(x).zfill(3) for x in range(1,15)]
# for now, testing on a single subject, with appropriate FS ID, this will have to be masked.
present_subject, FS_ID = 'sub-NA', 'NA_220813_12'

session_info = {'te': 0.025, 'pe_direction': 'y','epi_factor': 37, 'use_FS': True}

if not op.isdir(preprocessed_data_dir):
    os.makedirs(preprocessed_data_dir)

# i/o

datasource_templates = dict(func=present_subject + '/func/*{run_nr}_bold.nii.gz',
                                        topup=present_subject + '/fmap/*{run_nr}_topup.nii.gz',
                                        physio=present_subject + '/func/*{run_nr}_physio.log',
                                        events=present_subject + '/func/*{run_nr}_events.pickle',
                                        eye=present_subject + '/func/*{run_nr}_eyedata.edf'
)
datasource = SelectFiles(datasource_templates, base_directory = raw_data_dir, sort_filelist = True)
datasource.inputs.run_nr = list(range(1,7))
res = datasource.run()

print(res.outputs.func)
print(res.outputs.topup)

tua_wf = create_topup_workflow(session_info, name = 'topup_all')
tua_wf.inputs.inputspec.in_files = res.outputs.func
tua_wf.inputs.inputspec.alt_files = res.outputs.topup
tua_wf.inputs.inputspec.output_directory = op.join(preprocessed_data_dir, present_subject)
tua_wf.inputs.inputspec.conf_file = '/usr/local/fsl/etc/flirtsch/b02b0-empty.cnf'
tua_wf.inputs.inputspec.conf_file = '/usr/share/fsl/5.0/etc/flirtsch/b02b0.cnf'
# tua_wf.run()

motion_proc = create_motion_correction_workflow('moco')
motion_proc.inputs.inputspec.in_files = res.outputs.func

# motion_proc.inputs.inputspec.in_files = tua_wf.outputs.outputspec.out_files
motion_proc.inputs.inputspec.output_directory = op.join(preprocessed_data_dir, present_subject)
motion_proc.inputs.inputspec.which_file_is_EPI_space = 'middle'

# motion_proc.run()

reg = create_registration_workflow(session_info, name = 'reg')
reg.inputs.inputspec.EPI_space_file = motion_proc.outputs.outputspec.EPI_space_file
reg.inputs.inputspec.output_directory = op.join(preprocessed_data_dir, present_subject)
reg.inputs.inputspec.freesurfer_subject_ID = FS_ID
reg.inputs.inputspec.freesurfer_subject_dir = FS_subject_dir
reg.inputs.inputspec.T1_file = ''
reg.inputs.inputspec.standard_file = '/usr/local/fsl/data/standard/MNI152_T1_1mm_brain.nii.gz'

reg.run()


tua_wf.run('MultiProc', plugin_args={'n_procs': -1})


