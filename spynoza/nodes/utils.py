from __future__ import division, print_function


def EPI_file_selector(which_file, in_files):
    """Selects which EPI file will be the standard EPI space.
    Choices are: 'middle', 'last', 'first', or any integer in the list
    """
    import math
    import os

    if which_file == 'middle':          # middle from the list
        return in_files[int(math.floor(len(in_files)/2))]
    elif which_file == 'first':         # first from the list
        return in_files[0]
    elif which_file == 'last':          # last from the list
        return in_files[-1]
    elif type(which_file) == int:       # the xth from the list
        return in_files[which_file]
    elif os.path.isfile(which_file):    # take another file, not from the list
        return which_file
    else:
        raise Exception('value of which_file, %s, doesn\'t allow choosing an actual file.'%which_file)


def get_scaninfo(in_file):
    """ Extracts info from nifti file.

    Extracts affine, shape (x, y, z, t), dynamics (t), voxel-size and TR from
    a given nifti-file.

    Parameters
    ----------
    in_file : nifti-file (*.nii.gz or *.nii)
        Nifti file to extract info from.

    Returns
    -------
    TR : float
        Temporal resolution of functional scan
    shape : tuple
        Dimensions of scan (x, y, z, time)
    dyns : int
        Number of dynamics (time)
    voxsize : tuple
        Size of voxels (x, y, z = slice thickness)
    affine : np.ndarray
        Affine matrix.
    """
    import nibabel as nib

    nifti = nib.load(in_file)
    affine = nifti.affine
    shape = nifti.shape
    dyns = nifti.shape[-1]
    voxsize = nifti.header['pixdim'][1:4]
    TR = float(nifti.header['pixdim'][4])

    return TR, shape, dyns, voxsize, affine


def dyns_min_1(dyns):
    dyns_1 = dyns - 1
    return dyns_1


def concat_iterables(sub, sess=None):
    """ Concatenates subject and session iterables.

    Generates a subject/session output-directory for datasink.inputs.container.

    Inputs
    ------
    sub : str
        Subject-id (e.g. sub-001)
    sess : str
        Session-id (e.g. sess-001)

    Returns
    -------
    out_name : str
        Concatenation of iterables (if sess is defined)
    """
    import os

    if sess is None:
        out_name = sub
    else:
        out_name = os.path.join(sub, sess)

    return out_name


def topup_scan_params(pe_direction='y', te=0.025, epi_factor=37):

    import numpy as np
    import os
    import tempfile

    scan_param_array = np.zeros((2, 4))
    scan_param_array[0, ['x', 'y', 'z'].index(pe_direction)] = 1
    scan_param_array[1, ['x', 'y', 'z'].index(pe_direction)] = -1
    scan_param_array[:, -1] = te * epi_factor

    spa_txt = str('\n'.join(['\t'.join(['%1.3f'%s for s in sp]) for sp in scan_param_array]))

    fn = os.path.join(tempfile.gettempdir(), 'scan_params.txt')
    # with open(fn, 'wt', encoding='utf-8') as f:
    #     f.write(spa_txt)

    np.savetxt(fn, scan_param_array, fmt='%1.3f')
    return fn


def apply_scan_params(pe_direction='y', te=0.025, epi_factor=37, nr_trs=1):

    import numpy as np
    import os
    import tempfile

    scan_param_array = np.zeros((nr_trs, 4))
    scan_param_array[:, ['x', 'y', 'z'].index(pe_direction)] = 1
    scan_param_array[:, -1] = te * epi_factor

    spa_txt = str('\n'.join(['\t'.join(['%1.3f'%s for s in sp]) for sp in scan_param_array]))

    fn = os.path.join(tempfile.gettempdir(), 'scan_params_apply.txt')
    # with open(fn, 'wt', encoding='utf-8') as f:
    #     f.write(spa_txt)

    np.savetxt(fn, scan_param_array, fmt='%1.3f')
    return fn


def pickfirst(files):
    if isinstance(files, list):
        if len(files) > 0:
            return files[0]
        else:
            return files
    else:
        return files


def percent_signal_change(in_file, func = 'mean'):
    """Converts data in a nifti-file to percent signal change.

    Takes a 4D fMRI nifti-file and subtracts the
    mean data from the original data, after which division 
    by the mean or median and multiplication with 100.

    Parameters
    ----------
    in_file : str
        Absolute path to nifti-file.
    func : string ['mean', 'median'] (default: 'mean')
        the function used to calculate the first moment

    Returns
    -------
    out_file : str
        Absolute path to converted nifti-file.
    """

    import nibabel as nib
    import numpy as np
    import os
    import bottleneck as bn

    data = nib.load(in_file)
    dims = data.shape
    affine = data.affine
    header = data.header

    if func == 'mean':
        data_m = bn.nanmean(data.get_data(), axis=-1)
    elif func == 'median':
        data_m = bn.nanmedian(data.get_data(), axis=-1)

    data_psc = (100.0 * (np.nan_to_num(data.get_data()).transpose((3,0,1,2)) - data_m) / data_m).transpose((1,2,3,0))
    img = nib.Nifti1Image(np.nan_to_num(data_psc), affine=affine, header=header)

    new_name = os.path.basename(in_file).split('.')[:-2][0] + '_psc.nii.gz'
    out_file = os.path.abspath(new_name)
    nib.save(img, out_file)

    return out_file

def average_over_runs(in_files, func = 'mean'):
    """Converts data in a nifti-file to percent signal change.

    Takes a list of 4D fMRI nifti-files and averages them. 
    That is, the resulting file has the same dimensions as each
    of the input files. average_over_runs assumes that all nifti
    files to be averaged have identical dimensions.

    Parameters
    ----------
    in_files : list
        Absolute paths to nifti-files.
    func : string ['mean', 'median'] (default: 'mean')
        the function used to calculate the 'average'

    Returns
    -------
    out_file : str
        Absolute path to average nifti-file.
    """

    import nibabel as nib
    import numpy as np
    import os

    template_data = nib.load(in_files[0])
    dims = template_data.shape
    affine = template_data.affine
    header = template_data.header
    all_data = np.zeros([len(in_files)]+list(dims))
    
    for i in range(len(in_files)):
        d = nib.load(in_files[i])
        all_data[i] = d.get_data()

    if func == 'mean':
        av_data = all_data.mean(axis = 0)
    elif func == 'median':
        av_data = np.median(all_data, axis = 0)

    img = nib.Nifti1Image(av_data, affine=affine, header=header)

    new_name = os.path.basename(in_files[0]).split('.')[:-2][0] + '_av.nii.gz'
    out_file = os.path.abspath(new_name)
    nib.save(img, out_file)

    return out_file

def pickle_to_json(in_file):
    import json
    import jsonpickle
    import pickle
    import os.path as op

    with open(in_file, 'rU') as f:
        jsp = jsonpickle.encode(pickle.load(f))

    out_file = op.abspath(op.splitext(in_file)[0] + '.json')
    with open(out_file, 'w') as f:
        json.dump(jsp, f, indent = 2)

    return out_file


def set_nifti_intercept_slope(in_file, intercept = 0, slope = 1, in_is_out = True):
    """Sets the value-scaling intercept and slope in the nifti header.
    
    Parameters
    ----------
    in_file : string
        Absolute path to nifti-file.
    intercept : float (default: 0), can be None for nan value
        the intercept of the value scaling function
    slope : float (default: 1), can be None for nan value
        the slope of the value scaling function

    Returns
    -------
    out_file : str
        Absolute path to nifti-file.
    """

    import nibabel as nib
    import os

    if in_is_out:
        out_file = in_file
    else:
        out_file = os.path.basename(in_file).split('.')[:-2][0] + '_si.nii.gz'

    d = nib.load(in_file)
    d.header.set_slope_inter(slope = slope, inter = intercept)
    d.to_filename(os.path.abspath(out_file))

    return out_file

def split_4D_2_3D(in_file):
    """split_4D_2_3D splits a single 4D file into a list of nifti files.
    Because it splits the file at once, it's faster than fsl.ExtractROI
    
    Parameters
    ----------
    in_file : str
        Absolute path to nifti-file.

    Returns
    -------
    out_files : list
        List of absolute paths to nifti-files.    """

    import nibabel as nib
    import numpy as np
    import os
    import tempfile

    original_file = nib.load(in_file)
    dims = original_file.shape
    affine = original_file.affine
    header = original_file.header
    dyns = original_file.shape[-1]

    data = original_file.get_data()
    tempdir = tempfile.gettempdir()
    fn_base = os.path.split(in_file)[-1][:-7] # take off .nii.gz

    out_files = []
    for i in range(dyns):
        img = nib.Nifti1Image(data[...,i], affine=affine, header=header)
        opfn = os.path.join(tempdir, fn_base + '_%s.nii.gz'%str(i).zfill(4))
        nib.save(img, opfn)
        out_files.append(opfn)

    return out_files


def non_uniformity_correct_4D_file(in_file, auto_clip = False, clip_low = 7, clip_high = 200, n_procs = 12):
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

    uniformer = pe.MapNode(Uniformize(clip_high = clip_high, clip_low = clip_low, auto_clip = auto_clip, outputtype = 'NIFTI_GZ'), name='uniformer',
                    iterfield=['in_file'])
    merge = pe.MapNode(fsl.Merge(dimension='t'), name='merge', iterfield = ['in_files'])

    ########################################################################################
    datasink = pe.Node(nio.DataSink(infields=['topup'], container = ''), name='sinker')
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

