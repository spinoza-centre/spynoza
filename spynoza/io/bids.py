# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
from nipype.interfaces.io import IOBase
from nipype.interfaces.base import (
        traits, Str, BaseInterfaceInputSpec, TraitedSpec,
        File, Directory)
from bids.grabbids import BIDSLayout
import nibabel as nb



class BIDSGrabberInputSpec(BaseInterfaceInputSpec):
    subject = Str(desc='BID subject id')
    task = Str(True, usedefault=True, desc='BIDS task')
    run = traits.Int(mandatory=False, desc='BIDS Run')
    data_dir = Directory('/data/sourcedata',
                         usedefault=True)

class BIDSGrabberOutputSpec(TraitedSpec):
    bold = File(exists=True,
                desc='raw BOLD file')
    bold_metadata = traits.Dict(desc='Dictionary with BIDS metadata of bold file')
    fieldmap = File(exists=True, desc='Fieldmap data')
    fieldmap_metadata = traits.Dict(exists=True, desc='Dictionary with BIDS metadata of fieldmap file')

class BIDSGrabber(IOBase):
    input_spec = BIDSGrabberInputSpec
    output_spec = BIDSGrabberOutputSpec
    _always_run = True

    def _list_outputs(self):
        layout = BIDSLayout(self.inputs.data_dir)
        bold = layout.get(subject=self.inputs.subject,
                          task=self.inputs.task,
                          run=self.inputs.run,
                          type='bold')

        # Make sure there is only one nifti-file for this subject/task/run
        assert(len(bold) == 1)

        bold = bold[0].filename
        fieldmap = layout.get_fieldmap(bold)

        fieldmap = fieldmap[fieldmap['type']]
        bold_metadata = layout.get_metadata(bold)

        if 'NDynamics' not in bold_metadata:
            bold_metadata['NDynamics'] = nb.load(bold).shape[-1]

        fieldmap_metadata = layout.get_metadata(fieldmap)

        if 'NDynamics' not in fieldmap_metadata:
            fieldmap_metadata['NDynamics'] = nb.load(fieldmap).shape[-1]

        return {'bold':bold,
                'bold_metadata':bold_metadata,
                'fieldmap':fieldmap,
                'fieldmap_metadata':fieldmap_metadata}


