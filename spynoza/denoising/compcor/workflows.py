""" NOTES

- based on the awesome work by the fmriprep people

To do
- add cosine basis set
- add WM and global signal (global signal cf. power 2016, GSSCOR)
"""
import nipype.pipeline as pe
from nipype.interfaces.io import DataSink
from nipype.interfaces.utility import IdentityInterface, Merge, Rename
from nipype.algorithms.confounds import TCompCor, ACompCor
from nipype.interfaces import fsl
from .nodes import Erode_mask, Combine_component_files
from ...utils import Extract_task


def pick_wm(files):
    return files[2]


def pick_csf(files):
    return files[0]


def extract_basename(files):
    return [f.split('/')[-1] for f in files]


def create_compcor_workflow(name='compcor'):
    """ Creates A/T compcor workflow. """

    input_node = pe.Node(interface=IdentityInterface(fields=[
        'in_file',
        'fast_files',
        'highres2epi_mat',
        'n_comp_tcompcor',
        'n_comp_acompcor',
        'output_directory',
        'sub_id'
    ]), name='inputspec')

    output_node = pe.Node(interface=IdentityInterface(fields=[
        'tcompcor_file',
        'acompcor_file',
        'epi_mask'
    ]), name='outputspec')

    extract_task = pe.MapNode(interface=Extract_task,
                              iterfield=['in_file'], name='extract_task')

    rename_acompcor = pe.MapNode(interface=Rename(format_string='task-%(task)s_acompcor.tsv',
                                                  keepext=True),
                                 iterfield=['task', 'in_file'], name='rename_acompcor')

    datasink = pe.Node(DataSink(), name='sinker')
    datasink.inputs.parameterization = False

    average_func = pe.MapNode(interface=fsl.maths.MeanImage(dimension='T'),
                        name='average_func', iterfield=['in_file'])

    epi_mask = pe.MapNode(interface=fsl.BET(frac=.3, mask=True, no_output=True,
                                            robust=True),
                          iterfield=['in_file'], name='epi_mask')

    wm2epi = pe.MapNode(fsl.ApplyXFM(interp='nearestneighbour'),
                          iterfield=['reference'],
                          name='wm2epi')

    csf2epi = pe.MapNode(fsl.ApplyXFM(interp='nearestneighbour'),
                        iterfield=['reference'],
                        name='csf2epi')

    erode_csf = pe.MapNode(interface=Erode_mask, name='erode_csf',
                           iterfield=['epi_mask', 'in_file'])
    erode_csf.inputs.erosion_mm = 0
    erode_csf.inputs.epi_mask_erosion_mm = 30

    erode_wm = pe.MapNode(interface=Erode_mask, name='erode_wm',
                          iterfield=['epi_mask', 'in_file'])

    erode_wm.inputs.erosion_mm = 6
    erode_wm.inputs.epi_mask_erosion_mm = 10

    merge_wm_and_csf_masks = pe.MapNode(Merge(2), name='merge_wm_and_csf_masks',
                                        iterfield=['in1', 'in2'])

    # This should be fit on the 30mm eroded mask from CSF
    tcompcor = pe.MapNode(TCompCor(components_file='tcomcor_comps.txt'),
                          iterfield=['realigned_file', 'mask_files'],
                          name='tcompcor')

    # WM + CSF mask
    acompcor = pe.MapNode(ACompCor(components_file='acompcor_comps.txt',
                                   merge_method='union'),
                          iterfield=['realigned_file', 'mask_files'],
                          name='acompcor')

    compcor_wf = pe.Workflow(name=name)
    compcor_wf.connect(input_node, 'in_file', extract_task, 'in_file')
    compcor_wf.connect(extract_task, 'task_name', rename_acompcor, 'task')
    compcor_wf.connect(acompcor, 'components_file', rename_acompcor, 'in_file')

    compcor_wf.connect(input_node, 'sub_id', datasink, 'container')
    compcor_wf.connect(input_node, 'output_directory', datasink,
                       'base_directory')

    compcor_wf.connect(input_node, ('fast_files', pick_wm), wm2epi, 'in_file')
    compcor_wf.connect(epi_mask, 'mask_file', wm2epi, 'reference')
    compcor_wf.connect(input_node, 'highres2epi_mat', wm2epi, 'in_matrix_file')

    compcor_wf.connect(input_node, ('fast_files', pick_csf), csf2epi, 'in_file')
    compcor_wf.connect(epi_mask, 'mask_file', csf2epi, 'reference')
    compcor_wf.connect(input_node, 'highres2epi_mat', csf2epi, 'in_matrix_file')

    compcor_wf.connect(input_node, 'n_comp_tcompcor', tcompcor, 'num_components')
    compcor_wf.connect(input_node, 'n_comp_acompcor', acompcor, 'num_components')

    compcor_wf.connect(input_node, 'in_file', average_func, 'in_file')
    compcor_wf.connect(average_func, 'out_file', epi_mask, 'in_file')
    compcor_wf.connect(epi_mask, 'mask_file', erode_csf, 'epi_mask')
    compcor_wf.connect(epi_mask, 'mask_file', erode_wm, 'epi_mask')

    compcor_wf.connect(wm2epi, 'out_file', erode_wm, 'in_file')
    compcor_wf.connect(csf2epi, 'out_file', erode_csf, 'in_file')

    compcor_wf.connect(erode_wm, 'roi_eroded', merge_wm_and_csf_masks, 'in1')
    compcor_wf.connect(erode_csf, 'roi_eroded', merge_wm_and_csf_masks, 'in2')
    compcor_wf.connect(merge_wm_and_csf_masks, 'out', acompcor, 'mask_files')

    compcor_wf.connect(input_node, 'in_file', acompcor, 'realigned_file')
    compcor_wf.connect(input_node, 'in_file', tcompcor, 'realigned_file')
    compcor_wf.connect(erode_csf, 'epi_mask_eroded', tcompcor, 'mask_files')

    #compcor_wf.connect(tcompcor, 'components_file', output_node, 'acompcor_file')
    #compcor_wf.connect(acompcor, 'components_file', output_node, 'tcompcor_file')
    compcor_wf.connect(epi_mask, 'mask_file', output_node, 'epi_mask')

    compcor_wf.connect(rename_acompcor, 'out_file', datasink, 'acompcor_file')

    #compcor_wf.connect(tcompcor, 'components_file', combine_files, 'tcomp')
    #compcor_wf.connect(acompcor, 'components_file', combine_files, 'acomp')
    #compcor_wf.connect(combine_files, 'out_file', datasink, 'confounds')

    return compcor_wf
