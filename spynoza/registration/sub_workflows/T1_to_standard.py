def create_T1_to_standard_workflow(name='T1_to_standard', use_FS = True,
                                   do_fnirt = False, **kwargs):
    """Registers subject's T1 to standard space using FLIRT and FNIRT.
    Requires fsl tools
    Parameters
    ----------
    name : string
        name of workflow
    use_FS : bool
        whether to use freesurfer's T1
    Example
    -------
    >>> T1_to_standard = create_T1_to_standard_workflow()
    >>> T1_to_standard.inputs.inputspec.T1_file = 'T1.nii.gz'
    >>> T1_to_standard.inputs.inputspec.standard_file = 'standard.nii.gz'
    >>> T1_to_standard.inputs.inputspec.freesurfer_subject_ID = 'sub_01'
    >>> T1_to_standard.inputs.inputspec.freesurfer_subject_dir = '$SUBJECTS_DIR'

    Inputs::
          inputspec.T1_file : T1 anatomy file
          inputspec.standard_file : MNI? standard file
          inputspec.freesurfer_subject_ID : FS subject ID
          inputspec.freesurfer_subject_dir : $SUBJECTS_DIR
    Outputs::
           outputspec.T1_MNI_file : T1 converted to standard
           outputspec.out_matrix_file : mat file specifying how to convert T1 to standard
           outputspec.out_inv_matrix_file : mat file specifying how to convert standard to T1
           outputspec.warp_field_file : FNIRT warp field
           outputspec.warp_fieldcoeff_file : FNIRT warp coeff field
           outputspec.warped_file : FNIRT warped T1
           outputspec.out_intensitymap_file : FNIRT intensity map

    """

    import nipype.pipeline as pe
    from nipype.interfaces import fsl
    from nipype.interfaces import freesurfer
    from nipype.interfaces.utility import Function, IdentityInterface, Merge
    import nipype.interfaces.io as nio

    ### NODES
    input_node = pe.Node(IdentityInterface(
      fields=['freesurfer_subject_ID', 'freesurfer_subject_dir', 'T1_file', 'standard_file']), name='inputspec')

    # still have to choose which of these two output methods to use.

    datasink = pe.Node(nio.DataSink(), name='sinker')
    output_node = pe.Node(IdentityInterface(fields=['T1_standard_file', 
                    'T1_standard_matrix_file', 
                    'standard_T1_matrix_file',
                    'warp_field_file'
                    'warp_fieldcoeff_file',
                    'warped_file',
                    'modulatedref_file',
                    'out_intensitymap_file',
                    'T1_file'
                    ]), name='outputspec')

    # housekeeping function for finding T1 file in FS directory
    def FS_T1_file(freesurfer_subject_ID, freesurfer_subject_dir):
        import os.path as op
        return op.join(freesurfer_subject_dir, freesurfer_subject_ID, 'mri', 'T1.mgz')

    FS_T1_file_node = pe.Node(Function(input_names=('freesurfer_subject_ID', 'freesurfer_subject_dir'), output_names='T1_mgz_path',
                                     function=FS_T1_file), name='FS_T1_file_node')  

    T1_to_standard_workflow = pe.Workflow(name='T1_to_standard')

    # first link the workflow's output_directory into the datasink.
    # and immediately attempt to datasink the standard file
    T1_to_standard_workflow.connect(input_node, 'standard_file', datasink, 'reg.feat.standard.@nii.@gz')

    ########################################################################################
    # create FLIRT/FNIRT nodes
    ########################################################################################
    bet_N = pe.Node(interface=fsl.BET(vertical_gradient = -0.1, functional=False, mask=True), name='bet_N') 

    flirt_N = pe.Node(fsl.FLIRT(cost_func='normmi', output_type = 'NIFTI_GZ', dof = 12, interp = 'sinc'), 
                        name='flirt_N')
    if do_fnirt: 
        fnirt_N = pe.Node(fsl.FNIRT(in_fwhm=[8, 4, 2, 2],
                              subsampling_scheme=[4, 2, 1, 1],
                              warp_resolution =(6, 6, 6),
                              output_type='NIFTI_GZ'),
                        name='fnirt_N')

    ########################################################################################
    # first take file from freesurfer subject directory, if necessary
    # in which case we assume that there is no T1_file at present and overwrite it
    ########################################################################################
    if use_FS: 
        mriConvert_N = pe.Node(freesurfer.MRIConvert(out_type = 'niigz'), 
                          name = 'mriConvert_N')

        T1_to_standard_workflow.connect(input_node, 'freesurfer_subject_ID', FS_T1_file_node, 'freesurfer_subject_ID')
        T1_to_standard_workflow.connect(input_node, 'freesurfer_subject_dir', FS_T1_file_node, 'freesurfer_subject_dir')

        T1_to_standard_workflow.connect(FS_T1_file_node, 'T1_mgz_path', mriConvert_N, 'in_file')

        # and these are input into the flirt and fnirt operators, as below.
        T1_to_standard_workflow.connect(mriConvert_N, 'out_file', bet_N, 'in_file')
        T1_to_standard_workflow.connect(bet_N, 'out_file', flirt_N, 'in_file')
        T1_to_standard_workflow.connect(mriConvert_N, 'out_file', output_node, 'T1_file')
        if do_fnirt:
            T1_to_standard_workflow.connect(bet_N, 'out_file', fnirt_N, 'in_file')

    else:
        T1_to_standard_workflow.connect(input_node, 'T1_file', bet_N, 'in_file')
        T1_to_standard_workflow.connect(bet_N, 'out_file', flirt_N, 'in_file')
        T1_to_standard_workflow.connect(input_node, 'T1_file', output_node, 'T1_file')
        if do_fnirt:
            T1_to_standard_workflow.connect(bet_N, 'out_file', fnirt_N, 'in_file')


    ########################################################################################
    # continue with FLIRT step
    ########################################################################################
    T1_to_standard_workflow.connect(input_node, 'standard_file', flirt_N, 'reference')

    T1_to_standard_workflow.connect(flirt_N, 'out_matrix_file', output_node, 'T1_standard_matrix_file')
    T1_to_standard_workflow.connect(flirt_N, 'out_file', output_node, 'T1_standard_file')


    ########################################################################################
    # invert step
    ########################################################################################
    invert_N = pe.Node(fsl.ConvertXFM(invert_xfm = True), name = 'invert_N')
    T1_to_standard_workflow.connect(flirt_N, 'out_matrix_file', invert_N, 'in_file')
    T1_to_standard_workflow.connect(invert_N, 'out_file', output_node, 'standard_T1_matrix_file')

    if do_fnirt:
        ########################################################################################
        # FNIRT step
        ########################################################################################

        T1_to_standard_workflow.connect(flirt_N, 'out_matrix_file', fnirt_N, 'affine_file')
        T1_to_standard_workflow.connect(input_node, 'standard_file', fnirt_N, 'ref_file')

        ########################################################################################
        # output node
        ########################################################################################

        T1_to_standard_workflow.connect(fnirt_N, 'field_file', output_node, 'warp_field_file')
        T1_to_standard_workflow.connect(fnirt_N, 'fieldcoeff_file', output_node, 'warp_fieldcoeff_file')
        T1_to_standard_workflow.connect(fnirt_N, 'warped_file', output_node, 'warped_file')
        T1_to_standard_workflow.connect(fnirt_N, 'modulatedref_file', output_node, 'modulatedref_file')
        T1_to_standard_workflow.connect(fnirt_N, 'out_intensitymap_file', output_node, 'out_intensitymap_file')

    return T1_to_standard_workflow
