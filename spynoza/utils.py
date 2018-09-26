import nipype.pipeline as pe
from nipype.interfaces.utility import Function
import numpy as np
from nipype.interfaces.base import traits, File, BaseInterface, BaseInterfaceInputSpec, TraitedSpec
from nilearn.masking import compute_epi_mask
from nipype.interfaces import fsl
import nipype.interfaces.utility as niu

import os
import nibabel as nb
from nipype.utils.filemanip import fname_presuffix



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
    from nipype.utils.filemanip import split_filename

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

        d, fn, ext = split_filename(in_files[0])
        new_name = '{fn}_av{ext}'.format(fn=fn, ext=ext)
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



class CopyHeaderInputSpec(BaseInterfaceInputSpec):
    in_file = File(exists=True, mandatory=True, desc='the file we get the data from')
    hdr_file = File(exists=True, mandatory=True, desc='the file we get the header from')


class CopyHeaderOutputSpec(TraitedSpec):
    out_file = File(exists=True, desc='written file path')


class CopyHeader(BaseInterface):
    """
    Copy a header from the `hdr_file` to `out_file` with data drawn from
    `in_file`.
    """
    input_spec = CopyHeaderInputSpec
    output_spec = CopyHeaderOutputSpec

    def _run_interface(self, runtime):
        in_img = nb.load(self.inputs.hdr_file)
        out_img = nb.load(self.inputs.in_file)
        new_img = out_img.__class__(out_img.get_data(), in_img.affine, in_img.header)
        new_img.set_data_dtype(out_img.get_data_dtype())

        out_name = fname_presuffix(self.inputs.in_file,
                                   suffix='_fixhdr', newpath='.')
        new_img.to_filename(out_name)

        self._out_file = out_name

        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs['out_file'] = self._out_file
        return outputs

class ComputeEPIMaskInputSpec(BaseInterfaceInputSpec):
    in_file = File(exists=True, desc="3D or 4D EPI file")
    lower_cutoff = traits.Float(0.2, desc='lower cutoff', usedefault=True)
    upper_cutoff = traits.Float(0.85, desc='upper cutoff', usedefault=True)
    connected = traits.Bool(True, desc='if connected is True, only the largest connect component is kept.', usedefault=True)
    opening = traits.Int(2, desc='if opening is True, a morphological opening is performed,'
                                 'to keep only large structures.', usedefault=True)


class ComputeEPIMaskOutputSpec(TraitedSpec):
    mask_file = File(exists=True, desc="Binary brain mask")


class ComputeEPIMask(BaseInterface):
    input_spec = ComputeEPIMaskInputSpec
    output_spec = ComputeEPIMaskOutputSpec

    def _run_interface(self, runtime):
        mask_nii = compute_epi_mask(self.inputs.in_file, lower_cutoff=self.inputs.lower_cutoff, upper_cutoff=self.inputs.upper_cutoff,
                                    connected=self.inputs.connected, opening=self.inputs.opening)
        mask_nii.to_filename("mask_file.nii.gz")

        self._mask_file = os.path.abspath("mask_file.nii.gz")

        runtime.returncode = 0
        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs['mask_file'] = self._mask_file
        return outputs


class ReorientInputSpec(BaseInterfaceInputSpec):
    in_file = File(exists=True, mandatory=True,
                   desc='Input T1w image')


class ReorientOutputSpec(TraitedSpec):
    out_file = File(exists=True, desc='Reoriented T1w image')


class Reorient(BaseInterface):
    """Reorient a T1w image to RAS (left-right, posterior-anterior, inferior-superior)"""
    input_spec = ReorientInputSpec
    output_spec = ReorientOutputSpec

    def _run_interface(self, runtime):
        # Load image, orient as RAS
        fname = self.inputs.in_file
        orig_img = nb.load(fname)
        reoriented = nb.as_closest_canonical(orig_img)

        # Image may be reoriented
        if reoriented is not orig_img:
            out_name = fname_presuffix(fname, suffix='_ras', newpath=runtime.cwd)
            reoriented.to_filename(out_name)
        else:
            out_name = fname

        self._results = {}
        self._results['out_file'] = out_name

        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs.update(self._results)
        return outputs


def init_temporally_crop_run_wf(name='temporally_crop_wf',
                                in_files=None, 
                                templates=None, 
                                method='last'):
    """This workflow crops the nifti-file in in_file to give
    it the same number of timepoints as template
    
        Parameters
    ----------
    name : string
        name of workflow
        
    in_files : string
        data to be temporally cropped
    
    templates : string
        data that defines sizes
        
    method : string
        Where to crop. Possible values:
         * first
         * middle
         * last
        
    """
    
    wf = pe.Workflow(name=name)
    
    inputspec = pe.Node(niu.IdentityInterface(fields=['in_files', 'templates']),
                    name='inputspec')
    
    if in_files:
        inputspec.inputs.in_files = in_files
    
    if templates:
        inputspec.inputs.templates = templates
        
    get_num_scans_target = pe.MapNode(Function(function=get_scaninfo,
                                                output_names=['TR', 'shape', 'dyns', 'voxsize',
                                      'affine']),
                                      iterfield=['in_file'],
                        name='get_num_scans_target')
    
    get_num_scans_source = pe.MapNode(Function(function=get_scaninfo,
                                                output_names=['TR', 'shape', 'dyns', 'voxsize',
                                      'affine']),
                                      iterfield=['in_file'],                                      
                        name='get_num_scans_source')
    

    
    
    def get_extractroi_params(n_volumes_source, 
                              n_volumes_target,
                              method):        
        import numpy as np

        if method == 'last':
            t_min = np.max((n_volumes_source - n_volumes_target, 0))
        elif method == 'middle':
            t_min = int(n_volumes_source / 2)
        elif method == 'first':
            t_min = 0
        

        t_size = np.min((n_volumes_target, n_volumes_source - t_min))
        
        print(t_min, t_size)
        
        return t_min, t_size
    
    get_extractroi_params_node = pe.MapNode(Function(function=get_extractroi_params, 
                                                      output_names=['t_min', 't_size']),
                                            iterfield=['n_volumes_source', 'n_volumes_target'],
                                        name='get_extractroi_params_node')
    
    get_extractroi_params_node.inputs.method = method
    
    wf.connect(inputspec, 'in_files', get_num_scans_source, 'in_file')    
    wf.connect(inputspec, 'templates', get_num_scans_target, 'in_file')    
    
    wf.connect(get_num_scans_source, 'dyns', get_extractroi_params_node, 'n_volumes_source')
    wf.connect(get_num_scans_target, 'dyns', get_extractroi_params_node, 'n_volumes_target')
    
    extract_roi = pe.MapNode(fsl.ExtractROI(), 
                             iterfield=['in_file', 't_min', 't_size'],
                             name='extract_roi')
    wf.connect(get_extractroi_params_node, 't_min', extract_roi, 't_min')
    wf.connect(get_extractroi_params_node, 't_size', extract_roi, 't_size')
    wf.connect(inputspec, 'in_files', extract_roi, 'in_file')
    
    outputspec = pe.Node(niu.IdentityInterface(fields=['out_files']),
                        name='outputspec')
    
    wf.connect(extract_roi, 'roi_file', outputspec, 'out_files')
    
    return wf
    
    

def crop_anat_and_bold(bold, anat):
    from nilearn import image
    import os
    from nipype.utils.filemanip import split_filename

    _, bold_fn, bold_ext = split_filename(bold)
    _, anat_fn, anat_ext = split_filename(anat)

    bold_crop = image.crop_img(bold)
    anat_crop = image.resample_to_img(anat, bold_crop)
    
    bold_fn = os.path.abspath('{}_crop{}'.format(bold_fn, bold_ext))
    anat_fn = os.path.abspath('{}_crop{}'.format(anat_fn, anat_ext))

    bold_crop.to_filename(bold_fn)
    anat_crop.to_filename(anat_fn)

    return bold_fn, anat_fn
