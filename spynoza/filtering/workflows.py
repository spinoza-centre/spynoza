from nipype.workflows.fmri.fsl.preprocess import create_susan_smooth
import nipype.pipeline as pe
import nipype.interfaces.fsl as fsl
from nipype.interfaces.io import DataSink
from nipype.interfaces.utility import IdentityInterface, Merge, Select

"""
Most of this code has been generously provided by nipype:
http://nipype.readthedocs.io/en/latest/interfaces/generated/nipype.workflows.fmri.fsl.preprocess.html
"""

def getthreshop(thresh):
    return ['-thr %.10f -Tmin -bin' % (0.1 * val[1]) for val in thresh]


def pickfirst(files):
    if isinstance(files, list):
        return files[0]
    else:
        return files


def getbtthresh(medianvals):
    return [0.75 * val for val in medianvals]


def chooseindex(fwhm):
    if fwhm < 1:
        return [0]
    else:
        return [1]


def getmeanscale(medianvals):
    return ['-mul %.10f' % (10000. / val) for val in medianvals]


def getusans(x):
    return [[tuple([val[0], 0.75 * val[1]])] for val in x]

tolist = lambda x: [x]


def create_extended_susan_workflow(name='extended_susan', separate_masks=True):

    input_node = pe.Node(IdentityInterface(fields=['in_file',
                                                   'fwhm',
                                                   'EPI_session_space',
                                                   'output_directory',
                                                   'sub_id']), name='inputspec')

    output_node = pe.Node(interface=IdentityInterface(fields=['smoothed_files',
                                                              'mask',
                                                              'mean']), name='outputspec')

    datasink = pe.Node(DataSink(), name='sinker')
    datasink.inputs.parameterization = False

    # first link the workflow's output_directory into the datasink.

    esw = pe.Workflow(name=name)

    esw.connect(input_node, 'output_directory', datasink, 'base_directory')
    esw.connect(input_node, 'sub_id', datasink, 'container')

    meanfuncmask = pe.Node(interface=fsl.BET(mask=True,
                                             no_output=True,
                                             frac=0.3),
                           name='meanfuncmask')

    esw.connect(input_node, 'EPI_session_space', meanfuncmask, 'in_file')

    """
    Mask the functional runs with the extracted mask
    """

    maskfunc = pe.MapNode(interface=fsl.ImageMaths(suffix='_bet',
                                                   op_string='-mas'),
                          iterfield=['in_file'],
                          name='maskfunc')

    esw.connect(input_node, 'in_file', maskfunc, 'in_file')
    esw.connect(meanfuncmask, 'mask_file', maskfunc, 'in_file2')

    """
    Determine the 2nd and 98th percentile intensities of each functional run
    """

    getthresh = pe.MapNode(interface=fsl.ImageStats(op_string='-p 2 -p 98'),
                           iterfield=['in_file'],
                           name='getthreshold')
    esw.connect(maskfunc, 'out_file', getthresh, 'in_file')

    """
    Threshold the first run of the functional data at 10% of the 98th percentile
    """

    threshold = pe.MapNode(interface=fsl.ImageMaths(out_data_type='char',
                                                    suffix='_thresh'),
                           iterfield=['in_file', 'op_string'],
                           name='threshold')

    esw.connect(maskfunc, 'out_file', threshold, 'in_file')

    """
    Define a function to get 10% of the intensity
    """

    esw.connect(getthresh, ('out_stat', getthreshop), threshold, 'op_string')

    """
    Determine the median value of the functional runs using the mask
    """

    medianval = pe.MapNode(interface=fsl.ImageStats(op_string='-k %s -p 50'),
                           iterfield=['in_file', 'mask_file'],
                           name='medianval')
    esw.connect(input_node, 'in_file', medianval, 'in_file')
    esw.connect(threshold, 'out_file', medianval, 'mask_file')

    """
    Dilate the mask
    """

    dilatemask = pe.MapNode(interface=fsl.ImageMaths(suffix='_dil',
                                                     op_string='-dilF'),
                            iterfield=['in_file'],
                            name='dilatemask')
    esw.connect(threshold, 'out_file', dilatemask, 'in_file')
    esw.connect(dilatemask, 'out_file', output_node, 'mask')

    """
    Mask the motion corrected functional runs with the dilated mask
    """

    maskfunc2 = pe.MapNode(interface=fsl.ImageMaths(suffix='_mask',
                                                    op_string='-mas'),
                           iterfield=['in_file', 'in_file2'],
                           name='maskfunc2')
    esw.connect(input_node, 'in_file', maskfunc2, 'in_file')
    esw.connect(dilatemask, 'out_file', maskfunc2, 'in_file2')

    """
    Smooth each run using SUSAN with the brightness threshold set to 75%
    of the median value for each run and a mask constituting the mean
    functional
    """

    smooth = create_susan_smooth(separate_masks=separate_masks)

    esw.connect(input_node, 'fwhm', smooth, 'inputnode.fwhm')
    esw.connect(maskfunc2, 'out_file', smooth, 'inputnode.in_files')
    esw.connect(dilatemask, 'out_file', smooth, 'inputnode.mask_file')

    """
    Mask the smoothed data with the dilated mask
    """

    maskfunc3 = pe.MapNode(interface=fsl.ImageMaths(suffix='_mask',
                                                    op_string='-mas'),
                           iterfield=['in_file', 'in_file2'],
                           name='maskfunc3')
    esw.connect(smooth, 'outputnode.smoothed_files', maskfunc3, 'in_file')

    esw.connect(dilatemask, 'out_file', maskfunc3, 'in_file2')

    concatnode = pe.Node(interface=Merge(2),
                         name='concat')
    esw.connect(maskfunc2, ('out_file', tolist), concatnode, 'in1')
    esw.connect(maskfunc3, ('out_file', tolist), concatnode, 'in2')

    """
    The following nodes select smooth or unsmoothed data depending on the
    fwhm. This is because SUSAN defaults to smoothing the data with about the
    voxel size of the input data if the fwhm parameter is less than 1/3 of the
    voxel size.
    """
    selectnode = pe.Node(interface=Select(), name='select')

    esw.connect(concatnode, 'out', selectnode, 'inlist')

    esw.connect(input_node, ('fwhm', chooseindex), selectnode, 'index')
    esw.connect(selectnode, 'out', output_node, 'smoothed_files')

    """
    Scale the median value of the run is set to 10000
    """

    meanscale = pe.MapNode(interface=fsl.ImageMaths(suffix='_gms'),
                           iterfield=['in_file', 'op_string'],
                           name='meanscale')
    esw.connect(selectnode, 'out', meanscale, 'in_file')

    """
    Define a function to get the scaling factor for intensity normalization
    """

    esw.connect(medianval, ('out_stat', getmeanscale), meanscale, 'op_string')

    """
    Generate a mean functional image from the first run
    """

    meanfunc3 = pe.Node(interface=fsl.ImageMaths(op_string='-Tmean',
                                                 suffix='_mean'),
                        iterfield=['in_file'],
                        name='meanfunc3')

    esw.connect(meanscale, ('out_file', pickfirst), meanfunc3, 'in_file')
    esw.connect(meanfunc3, 'out_file', output_node, 'mean')

    # Datasink
    esw.connect(meanscale, 'out_file', datasink, 'filtering')
    esw.connect(selectnode, 'out', datasink, 'filtering.@smoothed')
    esw.connect(dilatemask, 'out_file', datasink, 'filtering.@mask')

    return esw


if __name__ == '__main__':
    import os.path as op
    test_data_path = '/media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data'
    smooth_wf = create_extended_susan_workflow(separate_masks=True)
    smooth_wf.base_dir = '/tmp/spynoza/workingdir'
    smooth_wf.inputs.inputspec.in_file = [op.join(test_data_path, 'sub-0020_gstroop_cut.nii.gz')]
    smooth_wf.inputs.inputspec.EPI_session_space = op.join(test_data_path, 'sub-0020_gstroop_meanbold.nii.gz')
    smooth_wf.inputs.inputspec.output_directory = '/tmp/spynoza'
    smooth_wf.inputs.inputspec.sub_id = 'sub-0020'
    smooth_wf.inputs.inputspec.fwhm = 5
    smooth_wf.run()
