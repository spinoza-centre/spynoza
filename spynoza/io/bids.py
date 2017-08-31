# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
from nipype.interfaces.io import IOBase
from nipype.interfaces.base import (
        traits, Str, BaseInterfaceInputSpec, TraitedSpec,
        File, Directory, OutputMultiPath)
from bids.grabbids import BIDSLayout
import nibabel as nb
import logging

iflogger = logging.getLogger('interface')


class BIDSGrabberInputSpec(BaseInterfaceInputSpec):
    subject_data = traits.Dict(Str, traits.Any)
    subject_id = Str()

class BIDSGrabberOutputSpec(TraitedSpec):
    out_dict = traits.Dict(desc='output data structure')
    fmap = OutputMultiPath(desc='output fieldmaps')
    bold = OutputMultiPath(desc='output functional images')
    sbref = OutputMultiPath(desc='output sbrefs')
    t1w = OutputMultiPath(desc='output T1w images')
    t2w = OutputMultiPath(desc='output T2w images')
    t1 = OutputMultiPath(desc='output T1 images')
    inv1 = OutputMultiPath(desc='output INV1 images')
    inv2 = OutputMultiPath(desc='output INV2 images')

class BIDSGrabber(IOBase):
    input_spec = BIDSGrabberInputSpec
    output_spec = BIDSGrabberOutputSpec
    _always_run = True

    def __init__(self, *args, **kwargs):
        anat_only = kwargs.pop('anat_only')
        super(BIDSGrabber, self).__init__(*args, **kwargs)
        if anat_only is not None:
            self._require_funcs = not anat_only

    def _list_outputs(self):
        bids_dict = self.inputs.subject_data
        
        outputs = {}
        outputs['out_dict'] = bids_dict
        outputs.update(bids_dict)
        
        if not bids_dict['t1w']:
            raise FileNotFoundError('No T1w images found for subject sub-{}'.format(
                self.inputs.subject_id))

        if self._require_funcs and not bids_dict['bold']:
            raise FileNotFoundError('No functional images found for subject sub-{}'.format(
                self.inputs.subject_id))

        for imtype in ['bold', 't2w', 'fmap', 'sbref', 'inv1', 'inv2', 't1']:
            if not bids_dict[imtype]:
                iflogger.warn('No \'{}\' images found for sub-{}'.format(
                    imtype, self.inputs.subject_id))

        return outputs

def collect_data(dataset, participant_label, anatomical_acq=None, task=None):
    layout = BIDSLayout(dataset)
    queries = {
        'fmap': {'subject': participant_label, 'modality': 'fmap',
                 'extensions': ['nii', 'nii.gz']},
        'bold': {'subject': participant_label, 'modality': 'func', 'type': 'bold',
                 'extensions': ['nii', 'nii.gz']},
        'sbref': {'subject': participant_label, 'modality': 'func', 'type': 'sbref',
                  'extensions': ['nii', 'nii.gz']},
        't2w': {'subject': participant_label, 'type': 'T2w',
                'extensions': ['nii', 'nii.gz']},
        't1w': {'subject': participant_label, 'type': 'T1w',
                'extensions': ['nii', 'nii.gz']},
        't1': {'subject': participant_label, 'type': 'T1',
                'extensions': ['nii', 'nii.gz']},
        'inv1': {'subject': participant_label, 'type': 'INV1',
                'extensions': ['nii', 'nii.gz']},
        'inv2': {'subject': participant_label, 'type': 'INV2',
                'extensions': ['nii', 'nii.gz']},
    }

    if task:
        queries['bold']['task'] = task

    if anatomical_acq:
        for field in ['t2w', 't1w', 't1', 'inv1', 'inv2']:
            queries[field]['acq'] = anatomical_acq

    return {modality: [x.filename for x in layout.get(**query)]
            for modality, query in queries.items()}, layout
