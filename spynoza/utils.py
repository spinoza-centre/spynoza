import nipype.pipeline as pe
from nipype.interfaces.utility import Function
import numpy as np


def set_postfix(in_file, postfix):
    """ Sets a postfix identifier for a specific filename. """
    import os.path as op
    return op.basename(in_file).replace('.nii.gz', '_%s' % postfix)

Set_postfix = Function(function=set_postfix,
                        input_names=['in_file', 'postfix'],
                        output_names=['out_file'])


def remove_extension(in_file, extension='.nii.gz'):
    return in_file.replace(extension, '')


Remove_extension = Function(function=remove_extension,
                            input_names=['in_file', 'extension'],
                            output_names=['out_file'])


def set_parameters_in_nodes(workflow, **kwargs):
    """ Sets parameters in nodes of a workflow.
    
    This function sets parameters of nodes in a workflow. It takes a variable amount of
    keyword-arguments, which should take the form of `'node_name'={'parameter': value_to_set}.
    A cool feature of this function is that it checks whether the node (node_name) is contained
    in a sub-workflow (or sub-sub-workflow, etc.) using a recursive call to itself.
    
    Parameters
    ----------
    workflow : a Nipype workflow object
        The workflow in which the nodes need to be altered.
    **kwargs : key-word arguments
        A variable amount of keyword-arguments (dicts) which take the form of
        'node_name': {'parameter': value_to_set}.
    """
    for node, options in kwargs.items():

        # Which nodes (or sub-workflows) are contained in the workflow?
        available_nodes = workflow.list_node_names()

        if node in available_nodes:
            # If it matches exactly (i.e. not a sub-workflow), get it
            node_inst = workflow.get_node(node)

        elif node in [n.split('.')[-1] for n in available_nodes]:
            # Probably a sub-workflow --> get ready to input this sub-wf to the function itself
            sub_wf_name = [n.split('.')[0] for n in available_nodes if node in n][0]
            sub_wf = workflow.get_node(sub_wf_name)
            sub_kwargs = {node: options}

            # Recursive call to itself
            sub_wf = set_parameters_in_nodes(sub_wf, **sub_kwargs)
            setattr(workflow, sub_wf_name, sub_wf)  # update workflow with updated sub_wf
            continue  # skip the rest
        else:
            msg = ("You want to set parameter(s) in node '%s' in workflow '%s' "
                   "but this node doesn't seem to exist. Known nodes: %r" %
                   (node, workflow.name, available_nodes))
            raise ValueError(msg)

        # Loop over options {parameter: value pairs} of node-instance
        for param, val in options.items():

            available_params = list(node_inst.inputs.__dict__.keys())

            if param in available_params:
                # Set input if param exists
                node_inst.set_input(param, val)
            else:
                msg = ("You want to set the parameter '%s' in node '%s' but "
                       "this parameter doesn't exist in this node. Known "
                       "parameters: %r" % (param, node, available_params))
                raise ValueError(msg)

        # update workflow with updated node-instance
        setattr(workflow, node, node_inst)

    return workflow


def extract_task(in_file):
    import os.path as op
    task_name = op.basename(in_file.split('task-')[-1].split('_')[0])
    return task_name


Extract_task = Function(function=extract_task,
                        input_names=['in_file'],
                        output_names=['task_name'])


def join_datasink_base(base, ext):
    import os.path as op
    out = op.join(base, ext)
    if isinstance(out, list):
        out = out[0]
    return out


Join_datasink_base = Function(function=join_datasink_base,
                              input_names=['base', 'ext'],
                              output_names=['out'])


def epi_file_selector(which_file, in_files):
    """Selects which EPI file will be the standard EPI space.
    Choices are: 'middle', 'last', 'first', or any integer in the list
    """
    import math
    import os

    if which_file == 'middle':  # middle from the list
        return in_files[int(math.floor(len(in_files) / 2))]
    elif which_file == 'first':  # first from the list
        return in_files[0]
    elif which_file == 'last':  # last from the list
        return in_files[-1]
    elif type(which_file) == int:  # the xth from the list
        return in_files[which_file]
    elif os.path.isfile(which_file):  # take another file, not from the list
        return which_file
    else:
        msg = ('value of which_file, %s, doesn\'t allow choosing an actual file.'
               % which_file)
        raise ValueError(msg)


EPI_file_selector = Function(function=epi_file_selector,
                             input_names=['which_file', 'in_files'],
                             output_names=['out_file'])


def pick_last(in_files):

    if isinstance(in_files, list):
        return in_files[-1]
    else:
        return in_files


def get_scaninfo(in_file):
    """ Extracts info from nifti file.

    Extracts affine, shape (x, y, z, t), dynamics (t), voxel-size and TR from
    a given nifti-file.

    Parameters
    ----------
    in_file : nifti-file (.nii.gz or .nii)
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


Get_scaninfo = Function(function=get_scaninfo,
                        input_names=['in_file'],
                        output_names=['TR', 'shape', 'dyns', 'voxsize',
                                      'affine'])


def dyns_min_1(dyns):
    dyns_1 = dyns - 1
    return dyns_1


Dyns_min_1 = Function(function=dyns_min_1, input_names=['dyns'],
                      output_names=['dyns_1'])

# ToDo: make concat_iterables work for arbitrary amount of iterables
def concat_iterables(iterables):
    """ Concatenates iterables (starting with subject).

    Parameters
    ----------
    iterables : list
        List of iterables to be concatenated into a path (e.g. after using
        nipype Merge-node).

    Returns
    -------
    out_name : str
        Concatenation of iterables
    """
    import os.path as op
    return op.join(*iterables)


Concat_iterables = Function(function=concat_iterables,
                            input_names=['iterables'],
                            output_names=['concatenated_path'])


def pickfirst(files):
    if isinstance(files, list):
        if len(files) > 0:
            return files[0]
        else:
            return files
    else:
        return files

def average_over_runs(in_files, func='mean', output_filename=None):
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
    output_filename : str
        path to output filename

    Returns
    -------
    out_file : str
        Absolute path to average nifti-file.
    """

    import nibabel as nib
    import numpy as np
    import os
    import bottleneck as bn

    template_data = nib.load(in_files[0])
    dims = template_data.shape
    affine = template_data.affine
    header = template_data.header
    all_data = np.zeros([len(in_files)] + list(dims))

    for i in range(len(in_files)):
        d = nib.load(in_files[i])
        all_data[i] = d.get_data()

    if func == 'mean':
        av_data = all_data.mean(axis=0)
    elif func == 'median':
        # weird reshape operation which hopeully fixes an issue in which
        # np.median hogs memory and lasts amazingly long
        all_data = all_data.reshape((len(in_files), -1))
        av_data = bn.nanmedian(all_data, axis=0)
        av_data = av_data.reshape(dims)

    img = nib.Nifti1Image(av_data, affine=affine, header=header)

    if output_filename == None:
        new_name = os.path.basename(in_files[0]).split('.')[:-2][
                       0] + '_av.nii.gz'
        out_file = os.path.abspath(new_name)
    else:
        out_file = os.path.abspath(output_filename)
    nib.save(img, out_file)

    return out_file


Average_over_runs = Function(function=average_over_runs,
                             input_names=['in_files', 'func',
                                          'output_filename'],
                             output_names=['out_file'])


def pickle_to_json(in_file):
    import json
    import jsonpickle
    import pickle
    import os.path as op

    with open(in_file, 'rU') as f:
        jsp = jsonpickle.encode(pickle.load(f))

    out_file = op.abspath(op.splitext(in_file)[0] + '.json')
    with open(out_file, 'w') as f:
        json.dump(jsp, f, indent=2)

    return out_file


Pickle_to_json = Function(function=pickle_to_json,
                          input_names=['in_file'],
                          output_names=['out_file'])


def set_nifti_intercept_slope(in_file, intercept=0, slope=1, in_is_out=True):
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
    d.header.set_slope_inter(slope=slope, inter=intercept)
    d.to_filename(os.path.abspath(out_file))

    return out_file


Set_nifti_intercept_slope = Function(function=set_nifti_intercept_slope,
                                     input_names=['in_file', 'intercept',
                                                  'slope', 'in_is_out'],
                                     output_names=['out_file'])


def split_4D_to_3D(in_file):
    """split_4D_to_3D splits a single 4D file into a list of nifti files.
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
    import os
    import tempfile

    original_file = nib.load(in_file)
    affine = original_file.affine
    header = original_file.header
    dyns = original_file.shape[-1]

    data = original_file.get_data()
    tempdir = tempfile.gettempdir()
    fn_base = os.path.split(in_file)[-1][:-7]  # take off .nii.gz

    out_files = []
    for i in range(dyns):
        img = nib.Nifti1Image(data[..., i], affine=affine, header=header)
        opfn = os.path.join(tempdir, fn_base + '_%s.nii.gz' % str(i).zfill(4))
        nib.save(img, opfn)
        out_files.append(opfn)

    return out_files


Split_4D_to_3D = Function(function=split_4D_to_3D, input_names=['in_file'],
                          output_names=['out_files'])
