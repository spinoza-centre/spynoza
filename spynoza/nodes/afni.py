from nipype.interfaces.afni.base import AFNICommand, AFNICommandInputSpec, AFNICommandOutputSpec
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath,
                                    isdefined, OutputMultiPath)

class UniformizeInputSpec(AFNICommandInputSpec):

    in_file = File(
    	argstr="-anat %s", 
    	exists=True, 
    	mandatory=True,
        desc="file to be unifized")
    clip_low = traits.Float(
    	6, 
    	argstr='-clip_low %f', 
    	desc="""Use LOW as the voxel intensity separating brain from air.
   NOTE: The historic clip_low value was 25.
      But that only works for certain types of input data and can
      result in bad output depending on the range of values in
      the input dataset.
      The new default sets -clip_low via -auto_clip option.""")    
    clip_high = traits.Float(
    	200, 
    	argstr='-clip_high %f', 
    	desc="""Do not include voxels with intensity higher
                  than HIGH in calculations.""")
    auto_clip = traits.Bool(
    	True, 
    	desc="""Automatically set the clip levels.
	LOW in a procedure similar to 3dClipLevel,
	HIGH is set to 3*LOW. (Default since Jan. 2011)""",
		argstr='-auto_clip', 
		usedefault=True)   
    niter = traits.Int(
    	5, 
    	desc="""Set the number of iterations for concentrating PDF
	Default is 5.""",
		argstr='-niter %d', 
		usedefault=True)   
    quiet = traits.Bool(
    	desc='Suppress output to screen',
		argstr='-q') 
    out_file = File(
        name_template='%s_uni',
        desc='output image file name',
        argstr='-prefix %s',
        name_source='in_file')    

class Uniformize(AFNICommand):
    _cmd = '3dUniformize'
    input_spec = UniformizeInputSpec
    output_spec = AFNICommandOutputSpec

