import os
import numpy as np
from nipype.interfaces.fsl.base import FSLCommand, FSLCommandInputSpec
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath,
                                    isdefined, OutputMultiPath)

class PreparePNMInput(FSLCommandInputSpec):
    in_file = File(position=2, argstr="-i %s", exists=True, mandatory=True,
                desc="physiological recordings")
    prefix = File(value='phys_recording', genfile=True, position=-2, argstr="-o %s", 
                  desc="prefix for output files", usedefault=True)
    resp_index = traits.Int(1, argstr='--resp=%d', usedefault=True)
    cardiac_index = traits.Int(2, argstr='--cardiac=%d', usedefault=True)
    trigger_index = traits.Int(3, argstr='--trigger=%d', usedefault=True)    
    smoothresp = traits.Float(0.1, argstr='--smoothresp=%f', usedefault=True)
    smoothcard = traits.Float(0.1, argstr='--smoothcard=%f', usedefault=True)
    sampling_rate = traits.Int(496, argstr='-s %d', desc='sampling_rate')
    tr = traits.Float(2.0, argstr='--tr=%f', usedefault=True)
    hr_rvt = traits.Bool(argstr='--heartrate --rvt',)
    
class PreparePNMOutput(TraitedSpec):
    time = File(exists=True, desc="Time triggers")
    card = File(exists=True, desc="Cardiac regressor")
    resp = File(exists=True, desc="Respiratory regressor")
    hr = File(exists=True, desc="Heartrate regressor")
    rvt = File(exists=True, desc="RVT regressor")
    
class PreparePNM(FSLCommand):
    _cmd = "popp"
    input_spec = PreparePNMInput
    output_spec = PreparePNMOutput
    _suffix = "_popp"
    def _list_outputs(self):
        outputs = self.output_spec().get()
        for key in ['time', 'resp', 'card', 'hr', 'rvt']:        
            outputs[key] = os.path.join(os.getcwd(), self.inputs.prefix + '_%s.txt' % key)
        return outputs
    
class PNMtoEVsInput(FSLCommandInputSpec):

    functional_epi = File(position=2, argstr="-i %s", exists=True, mandatory=True,
                desc="input image filename (of 4D functional/EPI data)")
    prefix = traits.String('pnm_regressors_', argstr="-o %s", exists=True, mandatory=True,
                 desc="output filename (for confound/EV matrix)", usedefault=True)
    tr = traits.Float(argstr="--tr=%s", exists=True, mandatory=True,
                desc="TR value in seconds") 
    cardiac = File(argstr='-c %s', exists=True, 
                   desc='input filename for cardiac values (1 or 2 columns: time [phase])')
    resp =  File(argstr='-r %s', exists=True, 
                   desc='input filename for respiratory phase values (1 or 2 columns: time [phase])')
    hr = File(argstr='--heartrate=%s', exists=True, desc='heartrate regressor')
    rvt = File(argstr='--rvt=%s', exists=True, desc='rvt regressor')
    order_cardiac = traits.Int(default_value=4, argstr='--oc=%d', usedefault=True,
                               desc='order of basic cardiac regressors (number of Fourier pairs) - default=4')
    order_resp = traits.Int(default_value=4, argstr='--or=%d',
                               desc='order of basic respiratory regressors (number of Fourier pairs) - default=4', 
                                            usedefault=True,)    
    order_cardiac_interact = traits.Int(default_value=2, argstr='--multc=%d',
                                           usedefault=True,
                               desc='order of basic cardiac regressors (number of Fourier pairs) - default=2')
    order_resp_interact = traits.Int(default_value=2, argstr='--multr=%d',
                                        usedefault=True,
                               desc='order of basic respiratory regressors (number of Fourier pairs) - default=2')    
    slice_dir = traits.Enum('x', 'y', 'z', argstr='--slicedir=%s',
                            desc='specify slice direction (x/y/z) - default is z')
    slice_order = traits.Enum('up', 'down', 'interleaved_up', 'interleaved_down', argstr='--sliceorder=%s',
                            desc='specify slice ordering (up/down/interleaved_up/interleaved_down)') 
    slice_timing = File(argstr='--slicetiming=%s',
                            desc='specify slice timing via an external file') 
    csf_mask = File(argstr='--csfmask=%s',
                            desc='filename of csf mask image (and generate csf regressor)') 
    verbose = traits.Bool(desc='switch on diagnostic messages',
                          argstr='-v')     
    
class PNMtoEVsOutput(TraitedSpec):
    evs = OutputMultiPath(File(desc='Set of nifti-files containing physiological'
                                    'regressors', exists=True))

class PNMtoEVs(FSLCommand):

    _cmd = "pnm_evs"
    input_spec = PNMtoEVsInput
    output_spec = PNMtoEVsOutput

    def _list_outputs(self):
        outputs = self.output_spec().get()
        
        n_evs = (self.inputs.order_cardiac + self.inputs.order_resp) * 2 + \
                (self.inputs.order_cardiac_interact * self.inputs.order_resp_interact) * 4 + \
                2
        
        outputs['evs'] = []
        for i in np.arange(1, n_evs+1):
            
            outputs['evs'].append(os.path.abspath(self.inputs.prefix + 'ev%03d.nii.gz' % i))
         
        return outputs



