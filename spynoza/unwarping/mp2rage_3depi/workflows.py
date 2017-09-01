import nipype.pipeline.engine as pe
import nipype.interfaces.utility as util
from nipype.interfaces import fsl
from nipype.interfaces import afni
from nipype.interfaces import ants
import pkg_resources

def create_3DEPI_registration_workflow(name='3d_epi_registration'):
    
    workflow = pe.Workflow(name=name)
    
    fields = ['INV2', 'T1_file', 'T1_EPI_file']
    
    inputnode = pe.Node(util.IdentityInterface(fields=fields), 
                        name='inputnode')
    
    automask = pe.Node(afni.Automask(outputtype='NIFTI_GZ'), 
                       name='mask_INV2')
    
    workflow.connect(inputnode, 'INV2', automask, 'in_file')
    
    mask_T1_EPI = pe.Node(fsl.ApplyMask(), name='mask_T1_EPI')
    
    workflow.connect(inputnode, 'T1_EPI_file', mask_T1_EPI, 'in_file')
    workflow.connect(automask, 'out_file', mask_T1_EPI, 'mask_file')
    
    
    json = pkg_resources.resource_filename('niworkflows.data', 't1-mni_registration_testing_002.json')
    reg = pe.Node(ants.Registration(from_file=json), name='registration')
    
    workflow.connect(mask_T1_EPI, 'out_file', reg, 'moving_image')
    workflow.connect(inputnode, 'T1_file', reg, 'fixed_image')
    
    outputnode = pe.Node(util.IdentityInterface(fields=['transform',
                                                        'transformed_T1_epi']),
                        name='outputnode')
    
    workflow.connect(reg, 'composite_transform', outputnode, 'transform')
    workflow.connect(reg, 'warped_image', outputnode, 'transformed_T1_epi')
    
    return workflow
    
    
