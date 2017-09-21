import nipype.pipeline.engine as pe
import nipype.interfaces.utility as niu
from nipype.interfaces import fsl
from nipype.interfaces import afni
from nipype.interfaces import ants
from nipype.interfaces import freesurfer
from nipype.interfaces.base import traits
import pkg_resources


def create_t1w_epi_registration_workflow(name='3d_epi_registration',
                                       linear_registration_parameters='linear_precise.json',
                                       nonlinear_registration_parameters='nonlinear_precise.json',
                                       num_threads_ants=4,
                                       init_reg_file=None):
    
    workflow = pe.Workflow(name=name)
    
    fields = ['INV2_epi', 'T1w', 'T1w_epi', 'bold_epi']
    
    inputspec = pe.Node(niu.IdentityInterface(fields=fields), 
                        name='inputspec')
    

    mc_bold = pe.MapNode(fsl.MCFLIRT(cost='normcorr',
                                     interpolation='sinc',
                                     save_mats=True,
                                     mean_vol=True),
                         iterfield=['in_file'],
                         name='mc_bold')

    workflow.connect(inputspec, 'bold_epi', mc_bold, 'in_file')

    mask_bold_epi = pe.MapNode(afni.Automask(outputtype='NIFTI_GZ'),
                               iterfield=['in_file'],
                               name='mask_bold_epi')

    workflow.connect(mc_bold, 'out_file', mask_bold_epi, 'in_file')

    meaner_bold = pe.MapNode(fsl.MeanImage(), iterfield=['in_file'], name='meaner_bold')
    workflow.connect(mc_bold, 'out_file', meaner_bold, 'in_file')
    


    # *** Mask T1w_EPI using INV2_epi variance ***
    mask_INV2_epi = pe.Node(afni.Automask(outputtype='NIFTI_GZ'), 
                       name='mask_INV2_epi')
    
    workflow.connect(inputspec, 'INV2_epi', mask_INV2_epi, 'in_file')
    
    mask_T1w_EPI = pe.Node(fsl.ApplyMask(), name='mask_T1w_EPI')
    
    workflow.connect(inputspec, 'T1w_epi', mask_T1w_EPI, 'in_file')
    workflow.connect(mask_INV2_epi, 'out_file', mask_T1w_EPI, 'mask_file')
    
    
    # *** Register EPI_bold to T1w_EPI (linear) ***
    bold_registration_json = pkg_resources.resource_filename('spynoza.data.ants_json', linear_registration_parameters)
    register_bold_epi2t1_epi = pe.MapNode(ants.Registration(from_file=bold_registration_json,
                                                            num_threads=num_threads_ants),
                                          iterfield=['moving_image'],
                                          name='register_bold_epi2t1_epi')
    workflow.connect(meaner_bold, 'out_file', register_bold_epi2t1_epi, 'moving_image')
    workflow.connect(mask_T1w_EPI, 'out_file', register_bold_epi2t1_epi, 'fixed_image')


    # *** Register T1w_EPI to T1w (non-linear) ***
    t1w_registration_json = pkg_resources.resource_filename('spynoza.data.ants_json', nonlinear_registration_parameters)

    if init_reg_file is not None:
        register_t1wepi_to_t1w = pe.Node(ants.Registration(from_file=t1w_registration_json,
                                                           num_threads=num_threads_ants), name='register_t1wepi_to_t1w')
        
        if init_reg_file.endswith('lta'):
            convert_to_ants = pe.Node(freesurfer.utils.LTAConvert(in_lta=init_reg_file,
                                                                 out_itk=True), name='convert_to_ants')

            workflow.connect(inputspec, 'T1w_epi', convert_to_ants, 'source_file')
            workflow.connect(inputspec, 'T1w', convert_to_ants, 'target_file')
            
            workflow.connect(convert_to_ants, 'out_itk', register_t1wepi_to_t1w, 'initial_moving_transform')
            
        else:
            reg.inputs.initial_moving_transform = init_reg_file

    else:
        register_t1wepi_to_t1w = pe.Node(ants.Registration(from_file=t1w_registration_json), name='register_t1wepi_to_t1w')        
    
    workflow.connect(mask_T1w_EPI, 'out_file', register_t1wepi_to_t1w, 'moving_image')
    workflow.connect(inputspec, 'T1w', register_t1wepi_to_t1w, 'fixed_image')

    merge_transforms = pe.MapNode(niu.Merge(2, axis='vstack'), iterfield=['in2'], name='merge_transforms')
    workflow.connect(register_bold_epi2t1_epi, 'forward_transforms', merge_transforms, 'in1')
    workflow.connect(register_t1wepi_to_t1w, ('forward_transforms', reverse), merge_transforms, 'in2')

    transform_mean_bold_epi = pe.MapNode(ants.ApplyTransforms(interpolation='LanczosWindowedSinc'),
                                    iterfield=['input_image', 'transforms'],
                                    name='transform_mean_bold_epi')

    workflow.connect(meaner_bold, 'out_file', transform_mean_bold_epi, 'input_image')
    workflow.connect(merge_transforms, ('out', reverse), transform_mean_bold_epi, 'transforms')
    workflow.connect(inputspec, 'T1w', transform_mean_bold_epi, 'reference_image')
    
    outputspec = pe.Node(niu.IdentityInterface(fields=['T1w_epi_to_T1w_transform',
                                                        'T1w_epi_to_T1w_transformed',
                                                         'motion_correction_parameters',
                                                         'bold_epi_mc',
                                                         'bold_epi_mask',
                                                         'bold_epi_to_T1w_epi_transform',
                                                         'bold_epi_to_T1w_epi_transformed',
                                                         'bold_epi_to_T1w_transforms',
                                                         'bold_epi_to_T1w_transformed',
                                                         'bold_epi_mean',
                                                         'masked_T1w_epi']),
                        name='outputspec')
    
    workflow.connect(register_t1wepi_to_t1w, 'forward_transforms', outputspec, 'T1w_epi_to_T1w_transform')
    workflow.connect(register_t1wepi_to_t1w, 'warped_image', outputspec, 'T1w_epi_to_T1w_transformed')

    workflow.connect(mc_bold, 'mat_file', outputspec, 'motion_correction_matrices')
    workflow.connect(mc_bold, 'out_file', outputspec, 'bold_epi_mc')
    workflow.connect(mask_bold_epi, 'out_file', outputspec, 'bold_epi_mask')
    workflow.connect(meaner_bold, 'out_file', outputspec, 'bold_epi_mean')

    workflow.connect(register_bold_epi2t1_epi, 'forward_transforms', outputspec, 'bold_epi_to_T1w_epi_transform')
    workflow.connect(register_bold_epi2t1_epi, 'warped_image', outputspec, 'bold_epi_to_T1w_epi_transformed')

    workflow.connect(merge_transforms, 'out', outputspec, 'bold_epi_to_T1w_transforms')
    workflow.connect(transform_mean_bold_epi, 'output_image', outputspec, 'bold_epi_to_T1w_transformed')

    workflow.connect(mask_T1w_EPI, 'out_file', outputspec, 'masked_T1w_epi')

    return workflow

def reverse(in_values):
    return in_values[::-1]
