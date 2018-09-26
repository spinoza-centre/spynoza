from .nodes import TopupScanParameters, QwarpPlusMinus
from ...io import BIDSGrabber
from ...utils import ComputeEPIMask, CopyHeader

import nipype.pipeline as pe
from nipype.interfaces import fsl
import nipype.interfaces.utility as util
import nipype.interfaces.io as nio

from nipype.interfaces import ants
from nipype.interfaces import afni

def create_topup_workflow(mode='average',
                          package='fsl',
                          name='topup_workflow', 
                          omp_nthreads=1,
                          base_dir='/home/neuro/workflow_folders'):

    inputspec = pe.Node(util.IdentityInterface(fields=['bold',
                                                       'bold_metadata',
                                                       'epi_op',
                                                       'epi_op_metadata']),
                        name='inputspec')

    workflow = pe.Workflow(name=name, base_dir=base_dir)

    # Make the warps compatbile with ANTS
    cphdr_warp = pe.Node(CopyHeader(), name='cphdr_warp')

    if package == 'fsl':
        # Create the parameter file that steers TOPUP
        topup_parameters = pe.Node(TopupScanParameters, name='topup_scanparameters')
        topup_parameters.inputs.mode = mode
        workflow.connect(inputspec, 'bold_metadata', topup_parameters, 'bold_metadata')
        workflow.connect(inputspec, 'epi_op_metadata', topup_parameters, 'epi_op_metadata')

        topup_node = pe.Node(fsl.TOPUP(args='-v'),
                                name='topup')

        workflow.connect(topup_parameters, 'encoding_file', topup_node, 'encoding_file')

        merge_list = pe.Node(util.Merge(2), name='merge_lists')
        workflow.connect(inputspec, 'bold', merge_list, 'in1')
        workflow.connect(inputspec, 'epi_op', merge_list, 'in2')

        merger = pe.Node(fsl.Merge(dimension='t'), name='merger')
        workflow.connect(merge_list, 'out', merger, 'in_files')
        workflow.connect(merger, 'merged_file', topup_node, 'in_file')
        workflow.connect(topup_node, ('out_warps', _pick_first), cphdr_warp, 'in_file')

    elif package == 'afni':

        def get_nodis_args(bold_metadata):
            bold_file_pe = bold_metadata["PhaseEncodingDirection"]

            args = '-noXdis -noYdis -noZdis'
            rm_arg = {'i': '-noXdis',
                      'j': '-noYdis',
                      'k': '-noZdis'}[bold_file_pe[0]]

            args = args.replace(rm_arg, '')

            return args

        qwarp = pe.Node(QwarpPlusMinus(pblur=[0.05, 0.05],
                                            blur=[-1, -1],
                                            noweight=True,
                                            minpatch=9,
                                            nopadWARP=True,
                                            environ={'OMP_NUM_THREADS': '%d' % omp_nthreads},

                                        outputtype='NIFTI_GZ',
                                        verb=True),
                        n_procs=omp_nthreads,
                        name='qwarp')

        workflow.connect(inputspec, ('bold_metadata', get_nodis_args), qwarp, 'args')
        workflow.connect(inputspec, 'bold', qwarp, 'in_file')
        workflow.connect(inputspec, 'epi_op', qwarp, 'base_file')
        workflow.connect(qwarp, 'source_warp', cphdr_warp, 'in_file')


    outputspec = pe.Node(util.IdentityInterface(fields=['bold_corrected',
                                                        'bold_unwarp_field',]),
                         name='outputspec')



    workflow.connect(inputspec, 'bold', cphdr_warp, 'hdr_file')

    to_ants = pe.Node(util.Function(function=_fix_hdr), name='to_ants')
    workflow.connect(cphdr_warp, 'out_file', to_ants, 'in_file')

    unwarp_bold = pe.Node(ants.ApplyTransforms(dimension=3,
                                                        float=True,
                                                        interpolation='LanczosWindowedSinc'),
                               name='unwarp_bold')

    workflow.connect(inputspec, 'bold', unwarp_bold, 'input_image')
    workflow.connect(to_ants, 'out', unwarp_bold, 'transforms')
    workflow.connect(inputspec, 'bold', unwarp_bold, 'reference_image')

    workflow.connect(to_ants, 'out', outputspec, 'bold_unwarp_field')
    workflow.connect(unwarp_bold, 'output_image', outputspec, 'bold_corrected')

    return workflow

# Helper functions
# --------------------

def _fix_hdr(in_file, newpath=None):
    import nibabel as nb
    from nipype.utils.filemanip import fname_presuffix

    nii = nb.load(in_file)
    hdr = nii.header.copy()
    hdr.set_data_dtype('<f4')
    hdr.set_intent('vector', (), '')
    out_file = fname_presuffix(in_file, "_warpfield", newpath=newpath)
    nb.Nifti1Image(nii.get_data().astype('<f4'), nii.affine, hdr).to_filename(
        out_file)
    return out_file


def _pick_first(l):
    return l[0]
