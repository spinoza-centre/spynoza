import nipype.pipeline as pe
from nipype.interfaces.utility import Function

# ToDo: not use a mutable argument for sg_args

def extend_motion_parameters(moco_par_file, tr, sg_args={'window_length': 120,
                                                          'deriv': 0,
                                                          'polyorder': 3,
                                                          'mode': 'nearest'}):
    import numpy as np
    from sklearn import decomposition
    from scipy.signal import savgol_filter

    ext_out_file = moco_par_file[:-7] + 'ext_moco_pars.par'
    new_out_file = moco_par_file[:-7] + 'new_moco_pars.par'

    sg_args['window_length'] = int(sg_args['window_length'] / tr)

    # Window must be odd-shaped
    if sg_args['window_length'] % 2 == 0:
        sg_args['window_length'] += 1

    moco_pars = np.loadtxt(moco_par_file)
    moco_pars = moco_pars - savgol_filter(moco_pars, axis = 0, **sg_args)

    dt_moco_pars = np.diff(np.vstack((np.ones((1,6)), moco_pars)), axis = 0)
    ddt_moco_pars = np.diff(np.vstack((np.ones((1,6)), dt_moco_pars)), axis = 0)

    ext_moco_pars = np.hstack((moco_pars, dt_moco_pars, ddt_moco_pars))

    # blow up using abs(), perform pca and take original number of 18 components
    amp = np.hstack((moco_pars, dt_moco_pars, ddt_moco_pars, dt_moco_pars**2,
                     ddt_moco_pars**2))
    pca = decomposition.PCA(n_components = 18)
    pca.fit(amp)
    new_moco_pars = pca.transform(amp)

    np.savetxt(new_out_file, new_moco_pars, fmt='%f', delimiter='\t')
    np.savetxt(ext_out_file, ext_moco_pars, fmt='%f', delimiter='\t')

    return new_out_file, ext_out_file

Extend_motion_pars = Function(input_names=['moco_par_file', 'tr'],
                              output_names=['new_out_file', 'ext_out_file'],
                              function=extend_motion_parameters)

def _check_if_iterable(to_iter, arg):

    if not isinstance(arg, list):
        arg = [arg] * len(to_iter)

    return arg

fix_iterable = pe.Node(Function(input_names=['to_iter', 'arg'], output_names='arg_fixed',
                                function=_check_if_iterable), name='fix_iterable')
