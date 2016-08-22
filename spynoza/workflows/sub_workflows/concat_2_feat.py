def create_concat_2_feat_workflow(name = 'concat_2_feat'):
    """Concatenates and inverts previously created fsl mat registration files.
    Requires fsl tools
    Parameters
    ----------
    name : string
        name of workflow
    Example
    -------
    >>> concat_2_feat = create_concat_2_feat_workflow()
    >>> concat_2_feat.inputs.inputspec.T1_file = 'T1.nii.gz'
    >>> concat_2_feat.inputs.inputspec.reference_file = 'standard.nii.gz'
    >>> concat_2_feat.inputs.inputspec.EPI_space_file = 'EPI.nii.gz'
    >>> concat_2_feat.inputs.inputspec.T1_standard_matrix_file = 'highres2standard.mat'
    >>> concat_2_feat.inputs.inputspec.standard_T1_matrix_file = 'standard2highres.mat'
    >>> concat_2_feat.inputs.inputspec.EPI_T1_matrix_file = 'example_func2highres.mat'
    >>> concat_2_feat.inputs.inputspec.T1_EPI_matrix_file = 'highres2example_func.mat'

    Inputs::
          inputspec.T1_file : T1 anatomy file
          inputspec.reference_file : standard standard file
          inputspec.EPI_space_file : EPI standard file
          inputspec.T1_standard_matrix_file : SE
          inputspec.standard_T1_matrix_file : SE
          inputspec.EPI_T1_matrix_file : SE
          inputspec.T1_EPI_matrix_file : SE
    Outputs::
           outputspec.standard_EPI_matrix_file : registration file that maps standard image to
                                 EPI space
           outputspec.EPI_standard_matrix_file : registration file that maps EPI image to
                                 standard space
    """
    import os.path as op
    import nipype.pipeline as pe
    from nipype.interfaces import fsl
    from nipype.interfaces import freesurfer
    from nipype.interfaces.utility import Function, IdentityInterface
    import nipype.interfaces.io as nio
    ### NODES
    input_node = pe.Node(IdentityInterface(
    fields=['T1_file', 'reference_file', 'EPI_space_file',
            'T1_standard_matrix_file', 'standard_T1_matrix_file', 'EPI_T1_matrix_file', 'T1_EPI_matrix_file'
           ]), name='inputspec')

    # still have to choose which of these two output methods to use.

    output_node = pe.Node(IdentityInterface(fields='out_file'), name='outputspec')

    concat_2_feat_workflow = pe.Workflow(name=name)

    # first link the workflow's output_directory into the datasink.
    # concat_2_feat_workflow.connect(input_node, 'output_directory', datasink, 'base_directory')

    ########################################################################################
    # concat step, from EPI to T1 to standard
    ########################################################################################
    concat_N = pe.Node(fsl.ConvertXFM(concat_xfm = True), name = 'concat_N')
    concat_2_feat_workflow.connect(input_node, 'EPI_T1_matrix_file', concat_N, 'in_file')
    concat_2_feat_workflow.connect(input_node, 'T1_standard_matrix_file', concat_N, 'in_file2')
    concat_2_feat_workflow.connect(concat_N, 'out_file', output_node, 'EPI_standard_matrix_file')

    ########################################################################################
    # invert step, to go from standard to T1 to EPI
    ########################################################################################
    invert_N = pe.Node(fsl.ConvertXFM(invert_xfm = True), name = 'invert_N')
    concat_2_feat_workflow.connect(concat_N, 'out_file', invert_N, 'in_file')
    concat_2_feat_workflow.connect(invert_N, 'out_file', output_node, 'standard_EPI_matrix_file')

    return concat_2_feat_workflow
