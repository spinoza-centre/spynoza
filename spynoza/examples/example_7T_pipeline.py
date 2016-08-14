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
from spynoza.workflows.topup_all import create_topup_all_workflow
from spynoza.workflows.sub_workflows import create_topup_workflow

# we will create a workflow from a BIDS formatted input, at first for the specific use case 
# of a 7T PRF experiment's preprocessing. 

# a project directory that we assume has already been created. 
preprocessed_data_dir = '/home/shared/2016/visual/PRF_7T/'
# raw_data_dir = '/home/raw_data/PRF_7T/data/BIDSdata/'
raw_data_dir = '/home/raw_data/PRF_7T/data/BIDSdata/'

# subject_list = ['sub-' + str(x).zfill(3) for x in range(1,15)]
present_subject = 'sub-EO'

if not op.isdir(preprocessed_data_dir):
    os.makedirs(preprocessed_data_dir)

# i/o

datasource1 = nio.DataGrabber(infields = ['run_nr'], outfields = ['func','topup','physio','events','eye'])
datasource1.inputs.base_directory = raw_data_dir
datasource1.inputs.template = '*'
datasource1.inputs.sort_filelist = True

datasource1.inputs.field_template = dict(func=present_subject + '/func/*%d_bold.nii.gz',
                                        topup=present_subject + '/fmap/*%d_topup.nii.gz',
                                        physio=present_subject + '/func/*%d_physio.log',
                                        events=present_subject + '/func/*%d_events.pickle',
                                        eye=present_subject + '/func/*%d_eyedata.edf'
)
datasource1.inputs.template_args = dict(func=[['run_nr']],
                                       topup=[['run_nr']],
                                       physio=[['run_nr']],
                                       events=[['run_nr']],
                                       eye=[['run_nr']])

datasource1.inputs.run_nr = list(range(1,3))
res = datasource1.run()

# datasource_templates = dict(func=present_subject + '/func/*{run_nr}_bold.nii.gz',
#                                         topup=present_subject + '/fmap/*{run_nr}_topup.nii.gz',
#                                         physio=present_subject + '/func/*{run_nr}_physio.log',
#                                         events=present_subject + '/func/*{run_nr}_events.pickle',
#                                         eye=present_subject + '/func/*{run_nr}_eyedata.edf'
# )
# datasource = SelectFiles(base_directory = raw_data_dir, sort_filelist = True, datasource_templates)
# res = datasource.run()

tua_wf = create_topup_all_workflow(session_info = {'te': 0.025,'alt_t': 0,'pe_direction': 'y','epi_factor': 37}, name = 'topup_all')
tua_wf.inputs.inputspec.in_files = res.outputs.func
tua_wf.inputs.inputspec.alt_files = res.outputs.topup
tua_wf.inputs.inputspec.output_directory = op.join(preprocessed_data_dir, present_subject)
tua_wf.inputs.inputspec.conf_file = '/usr/share/fsl/5.0/etc/flirtsch/b02b0-empty.cnf'
tua_wf.run()
# tua_wf.run('MultiProc', plugin_args={'n_procs': -1})