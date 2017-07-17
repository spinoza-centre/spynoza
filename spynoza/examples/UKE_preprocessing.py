#!/usr/bin/env python
import os
import sys
import os.path as op
import json
import nipype
from nipype import config, logging
import nibabel as nib
import argparse
from IPython import embed as shell

from UKE_preprocessing_workflow import create_preprocessing_workflow

# python UKE_preprocessing.py yesno /home/raw_data/UvA/Donner_lab/2017_eLife/1_fMRI_yesno_visual/ 01 01 /home/shared/UvA/spynoza_tryout/ --sub-FS-id AV_120414

def get_acquisition_parameters(analysis_parameters):
    # acquisition_parameters:
    acquisition_parameters = {}
    for parameters in [op.join(analysis_parameters["raw_data_dir"], param) for param in ['task-%s_bold.json'%analysis_parameters['task'], 'phasediff.json']]:
        # load the sequence parameters from json file
        with open(os.path.join(analysis_parameters["raw_data_dir"], parameters)) as f:
            json_s = f.read()
            acquisition_parameters.update(json.loads(json_s))
    analysis_parameters['EchoTimeDiff'] = acquisition_parameters['EchoTime2'] - acquisition_parameters['EchoTime1']
    return acquisition_parameters

def run(analysis_parameters, acquisition_parameters):
    preprocessing_workflow = create_preprocessing_workflow(analysis_parameters.update(acquisition_parameters),
                                                             name=analysis_parameters['task'])
    preprocessing_workflow.write_graph(os.path.join(analysis_parameters["opd"], analysis_parameters["task"])+'.pdf',
                                                             format='pdf', graph2use='colored')
    preprocessing_workflow.run('MultiProc', plugin_args={'n_procs': 24})

parser = argparse.ArgumentParser()
parser.add_argument("task", 
                    help='Name of the task to analyze. Determines which json file to load from BIDS folder') # Restrict bold to this task later
parser.add_argument("bids_folder", help='BIDS folder that contains raw data')
parser.add_argument("sub_id", help='Name of the subject to process / BIDS subject folder')
parser.add_argument("ses_id", help='Name of the session to process / BIDS session folder in subject folder')
parser.add_argument("output_folder", help='Output will be in output_folder/sub_id/ses_id')

parser.add_argument("--sub-FS-id", default=None, help='Freesurfer subject id, default sub-FS-id==sub_id') # Set to sub_id bty default
parser.add_argument("--topup", action='store_true', default=False,
                    help='Use topup correction instead of B0 unwarping.')
parser.add_argument("--no-field-correction", action='store_true', default=False,
                    help='Don\'t do any field correction')                                        
parser.add_argument("--mc-target", default="middle", dest='which_file_is_EPI_space',
                    help='Which EPI to use as motion correction target. Options are "first", "middle", "last", location, filename.')                    
parser.add_argument("--psc-func", default="median", dest='psc_func',
                    help='Use the median or the mean to conver to percent ignal change')
parser.add_argument("--slice-timing", default="order", dest='retroicor_order_or_timing',
                    help='"order" will compute relative slice timings from BIDS acquisition parameters. "timing" will use timings specified in BIDS acquition parameters.')
parser.add_argument("--mc-method", default="FSL", dest='moco_method',
                    help='Use "FSL" or "AFNI" for motion correction')
parser.add_argument("--sg-filter-order", default=3, dest='sg_filter_order',
                    help='Order of the Savitzky-Golay filter for temporal filtering.')
parser.add_argument("--sg-filter-length", default=120, dest='sg_filter_window_length',
                    help='Window length of the Savitzky-Golay filter for temporal filtering.')                                        
parser.add_argument("--retroicor", default=True, action='store_false', dest='perform_physio',
                    help='Don\'t perform retroicor to get rid of physiological nuisance variables')
parser.add_argument("--dry-run", default=False, action='store_true', dest='dry_run',
                    help='Print parameters but don\'t run preprocessing.')                    
args = parser.parse_args()
analysis_parameters = vars(args)
analysis_parameters.update({'do_FAST':1, 'use_AFNI_ss':0, 'do_fnirt':0, 'use_FS':1, 'FS_subject_dir':os.environ["SUBJECTS_DIR"], "hr_rvt":True})
analysis_parameters['opd'] = analysis_parameters['output_folder']
analysis_parameters['B0_or_topup'] = 'topup' if args.topup == True else 'B0'
analysis_parameters['sub_FS_id'] = args.sub_id if args.sub_FS_id is None else args.sub_FS_id
analysis_parameters['raw_data_dir'] = analysis_parameters['bids_folder']
analysis_parameters['sub_id'] = 'sub-{}'.format(analysis_parameters['sub_id'])
analysis_parameters['ses_id'] = 'ses-{}'.format(analysis_parameters['ses_id'])
analysis_parameters['output_directory'] = os.path.join(analysis_parameters["opd"], analysis_parameters["task"], analysis_parameters["sub_id"], analysis_parameters["ses_id"])
analysis_parameters['standard_file'] = os.path.join(os.environ['FSL_DIR'], 'data/standard/MNI152_T1_1mm_brain.nii.gz')
acquisition_parameters = get_acquisition_parameters(analysis_parameters)

if not args.dry_run:
    # create working directory
    try:
        os.makedirs(op.join(analysis_parameters["opd"], analysis_parameters["task"], analysis_parameters["sub_id"], analysis_parameters["ses_id"], 'log'))
    except OSError:
        pass
    
    # logging:
    config.update_config({  'logging': {'log_directory': op.join(analysis_parameters["opd"], analysis_parameters["task"], analysis_parameters["sub_id"], analysis_parameters["ses_id"], 'log'),
                                        'log_to_file': True,
                                        'workflow_level': 'INFO',
                                        'interface_level': 'DEBUG'},
                            'execution': {'stop_on_first_crash': True} })
    logging.update_logging(config)
    
    # run!
    run(analysis_parameters, acquisition_parameters)
else:
    print(analysis_parameters)
    print(acquisition_parameters)