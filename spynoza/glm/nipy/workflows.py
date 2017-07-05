from nipype.interfaces.utility import IdentityInterface
import nipype.pipeline as pe
from nipype.interfaces.io import DataSink
from nipype.interfaces.nipy.model import EstimateContrast, FitGLM
from ..workflows import create_modelgen_workflow


def create_firstlevel_workflow(name='level1'):

    input_node = pe.Node(IdentityInterface(fields=['events_file',
                                                   'func_file',
                                                   'TR',
                                                   'realignment_parameters',
                                                   'drift_model',
                                                   'contrasts',
                                                   'hrf_model',
                                                   'output_directory',
                                                   'sub_id']), name='inputspec')

    datasink = pe.Node(interface=DataSink(), name='datasink')
    datasink.inputs.parameterization = False

    fit_glm = pe.MapNode(interface=FitGLM(method='kalman', plot_design_matrix=True,
                                          normalize_design_matrix=True,
                                          save_residuals=True),
                         iterfield=['session_info'], name='fit_glm')

    estimate_contrast = pe.MapNode(interface=EstimateContrast(),
                                   iterfield=['beta', 'contrasts', 's2'], name='estimate_contrasts')

    firstlevel_wf = pe.Workflow(name=name)
    modelgen_wf = create_modelgen_workflow()
    firstlevel_wf.connect(input_node, 'events_file', modelgen_wf, 'inputspec.events_file')
    firstlevel_wf.connect(input_node, 'func_file', modelgen_wf, 'inputspec.func_file')
    firstlevel_wf.connect(input_node, 'TR', modelgen_wf, 'inputspec.TR')
    firstlevel_wf.connect(input_node, 'realignment_parameters', modelgen_wf, 'inputspec.realignment_parameters')
    firstlevel_wf.connect(input_node, 'TR', fit_glm, 'TR')
    firstlevel_wf.connect(input_node, 'drift_model', fit_glm, 'drift_model')
    firstlevel_wf.connect(input_node, 'hrf_model', fit_glm, 'hrf_model')
    firstlevel_wf.connect(input_node, 'contrasts', estimate_contrast, 'contrasts')
    firstlevel_wf.connect(input_node, 'output_directory', datasink, 'base_directory')
    firstlevel_wf.connect(input_node, 'sub_id', datasink, 'container')

    firstlevel_wf.connect(modelgen_wf, 'outputspec.session_info', fit_glm, 'session_info')
    firstlevel_wf.connect(fit_glm, 'beta', estimate_contrast, 'beta')
    firstlevel_wf.connect(fit_glm, 's2', estimate_contrast, 's2')
    firstlevel_wf.connect(fit_glm, 'dof', estimate_contrast, 'dof')
    firstlevel_wf.connect(fit_glm, 'axis', estimate_contrast, 'axis')
    firstlevel_wf.connect(fit_glm, 'nvbeta', estimate_contrast, 'nvbeta')
    firstlevel_wf.connect(fit_glm, 'constants', estimate_contrast, 'constants')
    firstlevel_wf.connect(fit_glm, 'reg_names', estimate_contrast, 'reg_names')

    firstlevel_wf.connect(fit_glm, 'beta', datasink, 'glm.beta')
    firstlevel_wf.connect(fit_glm, 's2', datasink, 'glm.@s2')
    firstlevel_wf.connect(fit_glm, 'nvbeta', datasink, 'glm.@nvbeta')
    firstlevel_wf.connect(fit_glm, 'constants', datasink, 'glm.@constants')
    firstlevel_wf.connect(fit_glm, 'reg_names', datasink, 'glm.@reg_names')
    firstlevel_wf.connect(fit_glm, 's2', datasink, 'glm.@squared_variance')
    firstlevel_wf.connect(fit_glm, 'residuals', datasink, 'glm.@residuals')

    firstlevel_wf.connect(estimate_contrast, 'p_maps', datasink, 'con')
    firstlevel_wf.connect(estimate_contrast, 'stat_maps', datasink, 'con.@stats')
    firstlevel_wf.connect(estimate_contrast, 'z_maps', datasink, 'con.@zmaps')

    return firstlevel_wf
