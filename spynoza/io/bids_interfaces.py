# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
from nipype.interfaces.io import IOBase
from nipype.interfaces.base import (
        traits, Str, BaseInterfaceInputSpec, TraitedSpec,
        File, Directory, OutputMultiPath, InputMultiPath,
        isdefined, DynamicTraitedSpec)
#from bids.grabbids import BIDSLayout
from bids import BIDSLayout
import nibabel as nb
import logging
import os
import os.path as op
from shutil import copy, copytree, rmtree, copyfileobj
import re
import gzip

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

class DerivativesDataSinkInputSpec(DynamicTraitedSpec, BaseInterfaceInputSpec):
    base_directory = traits.Directory(
        desc='Path to the base directory for storing data.')
    in_file = InputMultiPath(File(exists=True), mandatory=True,
                             desc='the object to be saved')
    source_file = File(exists=False, mandatory=True, desc='the input func file')
    suffix = traits.Str('', mandatory=True, desc='suffix appended to source_file')
    extra_values = traits.List(traits.Str)


class DerivativesDataSinkOutputSpec(TraitedSpec):
    out_file = OutputMultiPath(File(exists=True, desc='written file path'))


class DerivativesDataSink(IOBase):
    """
    Taken from the fmriprep-guys
    Saves the `in_file` into a BIDS-Derivatives folder provided
    by `base_directory`, given the input reference `source_file`.
    >>> import tempfile
    >>> from fmriprep.utils.bids import collect_data
    >>> tmpdir = tempfile.mkdtemp()
    >>> tmpfile = os.path.join(tmpdir, 'a_temp_file.nii.gz')
    >>> open(tmpfile, 'w').close()  # "touch" the file
    >>> dsink = DerivativesDataSink(base_directory=tmpdir)
    >>> dsink.inputs.in_file = tmpfile
    >>> dsink.inputs.source_file = collect_data('ds114', '01')[0]['t1w'][0]
    >>> dsink.inputs.suffix = 'target-mni'
    >>> res = dsink.run()
    >>> res.outputs.out_file  # doctest: +ELLIPSIS
    '.../fmriprep/sub-01/ses-retest/anat/sub-01_ses-retest_T1w_target-mni.nii.gz'
    """
    input_spec = DerivativesDataSinkInputSpec
    output_spec = DerivativesDataSinkOutputSpec
    _always_run = True

    def __init__(self, **inputs):
        super(DerivativesDataSink, self).__init__(**inputs)

    def _list_outputs(self):
        src_fname, _ = _splitext(self.inputs.source_file)
        _, ext = _splitext(self.inputs.in_file[0])
        compress = ext == '.nii'
        if compress:
            ext = '.nii.gz'

        BIDS_NAME = re.compile(
            '^(.*\/)?(?P<subject_id>sub-[a-zA-Z0-9]+)(_(?P<session_id>ses-[a-zA-Z0-9]+))?'
            '(_(?P<task_id>task-[a-zA-Z0-9]+))?(_(?P<acq_id>acq-[a-zA-Z0-9]+))?'
            '(_(?P<rec_id>rec-[a-zA-Z0-9]+))?(_(?P<run_id>run-[a-zA-Z0-9]+))?')
        m = BIDS_NAME.search(src_fname)

        # TODO this quick and dirty modality detection needs to be implemented
        # correctly
        mod = 'func'
        if 'anat' in op.dirname(self.inputs.source_file):
            mod = 'anat'
        elif 'dwi' in op.dirname(self.inputs.source_file):
            mod = 'dwi'
        elif 'fmap' in op.dirname(self.inputs.source_file):
            mod = 'fmap'

        base_directory = os.getcwd()
        if isdefined(self.inputs.base_directory):
            base_directory = op.abspath(self.inputs.base_directory)

        out_path = '{subject_id}'.format(**m.groupdict())
        if m.groupdict().get('session_id') is not None:
            out_path += '/{session_id}'.format(**m.groupdict())
        out_path += '/{}'.format(mod)

        out_path = op.join(base_directory, out_path)

        os.makedirs(out_path, exist_ok=True)

        base_fname = op.join(out_path, src_fname)

        formatstr = '{bname}_{suffix}{ext}'
        if len(self.inputs.in_file) > 1 and not isdefined(self.inputs.extra_values):
            formatstr = '{bname}_{suffix}{i:04d}{ext}'

        outputs = {'out_file':[]}

        for i, fname in enumerate(self.inputs.in_file):
            out_file = formatstr.format(
                bname=base_fname,
                suffix=self.inputs.suffix,
                i=i,
                ext=ext)
            if isdefined(self.inputs.extra_values):
                out_file = out_file.format(extra_value=self.inputs.extra_values[i])
            outputs['out_file'].append(out_file)
            if compress:
                with open(fname, 'rb') as f_in:
                    with gzip.open(out_file, 'wb') as f_out:
                        copyfileobj(f_in, f_out)
            else:
                copy(fname, out_file)


        return outputs

def _splitext(fname):
    fname, ext = op.splitext(op.basename(fname))
    if ext == '.gz':
        fname, ext2 = op.splitext(fname)
        ext = ext2 + ext
    return fname, ext


def test_derivatives_sink():
    from spynoza.io.bids import DerivativesDataSink
    ds = DerivativesDataSink()
    ds.inputs.source_file = '/data/sourcedata/sub-012/func/sub-012_task-binoculardots055_run-1_bold.nii.gz' 
    ds.inputs.suffix = 'mean'
    ds.inputs.base_directory = '/data/derivatives/mean_bold'
    ds.inputs.in_file = '/data/workflow_folders/topup/func_topup_task_binoculardots055_run_1_wf/meaner_bold/sub-012_task-binoculardots055_run-1_bold_masked_mcf_mean.nii.gz'
    return ds.run()
    

if __name__ == '__main__':
    test_derivatives_sink()
