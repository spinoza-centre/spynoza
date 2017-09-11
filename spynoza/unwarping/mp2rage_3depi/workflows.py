import nipype.pipeline.engine as pe
import nipype.interfaces.utility as niu
from nipype.interfaces import fsl
from nipype.interfaces import afni
from nipype.interfaces import ants
from nipype.interfaces import freesurfer
from nipype.interfaces.base import traits
import pkg_resources


def create_3DEPI_registration_workflow(name='3d_epi_registration',
                                       init_reg_file=None):
    
    workflow = pe.Workflow(name=name)
    
    fields = ['INV2', 'T1w_file', 'T1w_EPI_file', 'bold_EPIs']
    
    inputnode = pe.Node(niu.IdentityInterface(fields=fields), 
                        name='inputnode')
    

    mc_bold = pe.MapNode(fsl.MCFLIRT(cost='normcorr',
                                     interpolation='sinc',
                                     save_mats=True,
                                     mean_vol=True),
                         iterfield=['in_file'],
                         name='mc_bold')

    workflow.connect(inputnode, 'bold_EPIs', mc_bold, 'in_file')

    mask_bold_EPIs = pe.MapNode(afni.Automask(outputtype='NIFTI_GZ'),
                               iterfield=['in_file'],
                               name='mask_bold_epi')

    workflow.connect(mc_bold, 'out_file', mask_bold_EPIs, 'in_file')

    meaner_bold = pe.MapNode(fsl.MeanImage(), iterfield=['in_file'], name='meaner_bold')
    workflow.connect(mc_bold, 'out_file', meaner_bold, 'in_file')
    


    # *** Mask T1w_EPI using INV2 variance ***
    mask_INV2 = pe.Node(afni.Automask(outputtype='NIFTI_GZ'), 
                       name='mask_INV2')
    
    workflow.connect(inputnode, 'INV2', mask_INV2, 'in_file')
    
    mask_T1w_EPI = pe.Node(fsl.ApplyMask(), name='mask_T1w_EPI')
    
    workflow.connect(inputnode, 'T1w_EPI_file', mask_T1w_EPI, 'in_file')
    workflow.connect(mask_INV2, 'out_file', mask_T1w_EPI, 'mask_file')
    
    
    # *** Register EPI_bold to T1w_EPI (linear) ***
    bold_registration_json = pkg_resources.resource_filename('spynoza.data.ants_json', 'linear_precise.json')
    register_bold_epi2t1_epi = pe.MapNode(ants.Registration(from_file=bold_registration_json),
                                          iterfield=['moving_image'],
                                          name='register_bold_epi2t1_epi')
    workflow.connect(meaner_bold, 'out_file', register_bold_epi2t1_epi, 'moving_image')
    workflow.connect(mask_T1w_EPI, 'out_file', register_bold_epi2t1_epi, 'fixed_image')


    # *** Register T1w_EPI to T1w (non-linear) ***
    t1w_registration_json = pkg_resources.resource_filename('spynoza.data.ants_json', 'nonlinear_precise.json')

    if init_reg_file is not None:
        register_t1wepi_to_t1w = pe.Node(ants.Registration(from_file=t1w_registration_json), name='register_t1wepi_to_t1w')
        
        if init_reg_file.endswith('lta'):
            convert_to_ants = pe.Node(freesurfer.utils.LTAConvert(in_lta=init_reg_file,
                                                                 out_itk=True), name='convert_to_ants')

            workflow.connect(inputnode, 'T1w_EPI_file', convert_to_ants, 'source_file')
            workflow.connect(inputnode, 'T1w_file', convert_to_ants, 'target_file')
            
            workflow.connect(convert_to_ants, 'out_itk', register_t1wepi_to_t1w, 'initial_moving_transform')
            
        else:
            reg.inputs.initial_moving_transform = init_reg_file

    else:
        register_t1wepi_to_t1w = pe.Node(ants.Registration(from_file=json), name='register_t1wepi_to_t1w')        
    
    workflow.connect(mask_T1w_EPI, 'out_file', register_t1wepi_to_t1w, 'moving_image')
    workflow.connect(inputnode, 'T1w_file', register_t1wepi_to_t1w, 'fixed_image')

    merge_transforms = pe.MapNode(niu.Merge(2, axis='vstack'), iterfield=['in2'], name='merge_transforms')
    workflow.connect(register_t1wepi_to_t1w, 'forward_transforms', merge_transforms, 'in1')
    workflow.connect(register_bold_epi2t1_epi, 'forward_transforms', merge_transforms, 'in2')

    transform_mean_bold_epi = pe.MapNode(ants.ApplyTransforms(interpolation='LanczosWindowedSinc'),
                                    iterfield=['input_image', 'transforms'],
                                    name='transform_mean_bold_epi')

    workflow.connect(meaner_bold, 'out_file', transform_mean_bold_epi, 'input_image')
    workflow.connect(merge_transforms, 'out', transform_mean_bold_epi, 'transforms')
    workflow.connect(inputnode, 'T1w_file', transform_mean_bold_epi, 'reference_image')
    
    outputnode = pe.Node(niu.IdentityInterface(fields=['T1w_epi_to_T1w_transform',
                                                        'T1w_epi_to_T1w_transformed',
                                                         'motion_correction_parameters',
                                                         'motion_correction_matrices',
                                                         'motion_corrected_files',
                                                         'bold_epi_to_T1w_epi_transform',
                                                         'bold_epi_to_T1w_epi_transformed',
                                                         'bold_epi_to_T1w_transform',
                                                         'bold_epi_to_T1w_transformed',
                                                         'mean_bold',
                                                         'masked_T1w_epi']),
                        name='outputnode')
    
    workflow.connect(register_t1wepi_to_t1w, 'composite_transform', outputnode, 'T1w_epi_to_T1w_transform')
    workflow.connect(register_t1wepi_to_t1w, 'warped_image', outputnode, 'T1w_epi_to_T1w_transformed')

    workflow.connect(mc_bold, 'out_file', outputnode, 'motion_corrected_files')
    workflow.connect(mc_bold, 'mat_file', outputnode, 'motion_correction_matrices')
    workflow.connect(mc_bold, 'par_file', outputnode, 'motion_correction_parameters')

    workflow.connect(register_bold_epi2t1_epi, 'composite_transform', outputnode, 'bold_epi_to_T1w_epi_transform')
    workflow.connect(register_bold_epi2t1_epi, 'warped_image', outputnode, 'bold_epi_to_T1w_epi_transformed')

    workflow.connect(merge_transforms, 'out', outputnode, 'bold_epi_to_T1w_transform')
    workflow.connect(transform_mean_bold_epi, 'output_image', outputnode, 'bold_epi_to_T1w_transformed')

    workflow.connect(meaner_bold, 'out_file', outputnode, 'mean_bold')
    workflow.connect(mask_T1w_EPI, 'out_file', outputnode, 'masked_T1w_epi')

    return workflow
