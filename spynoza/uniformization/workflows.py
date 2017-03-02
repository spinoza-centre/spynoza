def non_uniformity_correct_4D_file(in_file, auto_clip=False, clip_low=7,
                                   clip_high=200, n_procs=12):
    """non_uniformity_correct_4D_file corrects functional files for nonuniformity on a timepoint by timepoint way.
    Internally it implements a workflow to split the in_file, correct each separately and then merge them back together.
    This is an ugly workaround as we have to find the output of the workflow's datasink somewhere, but it should work.

    Parameters
    ----------
    in_file : str
        Absolute path to nifti-file.
    auto_clip : bool (default: False)
        whether to let 3dUniformize decide on clipping boundaries
    clip_low : float (default: 7),
        lower clipping bound for 3dUniformize
    clip_high : float (default: 200),
        higher clipping bound for 3dUniformize
    n_procs : int (default: 12),
        the number of processes to run the internal workflow with

    Returns
    -------
    out_file : non-uniformity corrected file
        List of absolute paths to nifti-files.    """
    import glob
    import tempfile
    import os

    import nipype.pipeline as pe
    import nipype.interfaces.io as nio
    from nipype.interfaces.utility import Function, IdentityInterface
    import nipype.interfaces.fsl as fsl
    from spynoza.nodes.afni import Uniformize
    from spynoza.nodes.utils import split_4D_2_3D

    fn_base = os.path.split(in_file)[-1][:-7]
    td = tempfile.gettempdir()

    # nodes
    input_node = pe.Node(IdentityInterface(
        fields=['in_file',
                'auto_clip',
                'clip_low',
                'clip_high',
                ]), name='inputspec')
    split = pe.Node(Function(input_names='in_file', output_names=['out_files'],
                             function=split_4D_2_3D), name='split')

    uniformer = pe.MapNode(
        Uniformize(clip_high=clip_high, clip_low=clip_low, auto_clip=auto_clip,
                   outputtype='NIFTI_GZ'), name='uniformer',
        iterfield=['in_file'])
    merge = pe.MapNode(fsl.Merge(dimension='t'), name='merge',
                       iterfield=['in_files'])

    datasink = pe.Node(nio.DataSink(infields=['topup'], container=''),
                       name='sinker')
    datasink.inputs.parameterization = False

    datasink.inputs.base_directory = td

    # workflow
    nuc_wf = pe.Workflow(name='nuc')

    nuc_wf.connect(input_node, 'in_file', split, 'in_file')
    nuc_wf.connect(split, 'out_files', uniformer, 'in_file')
    nuc_wf.connect(uniformer, 'out_file', merge, 'in_files')
    nuc_wf.connect(merge, 'merged_file', datasink, 'uni')

    nuc_wf.inputs.inputspec.in_file = in_file

    nuc_wf.run('MultiProc', plugin_args={'n_procs': n_procs})

    out_file = glob.glob(os.path.join(td, 'uni', fn_base + '_0000*.nii.gz'))[0]

    return out_file
