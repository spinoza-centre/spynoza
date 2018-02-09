from nipype.interfaces.utility import Function


def rename_feat_dir(feat_dir, task):
    """ Renames the FEAT directory from fsl.FEAT.

    Mimicks nipype.utility.Rename, but Rename doesn't
    work for directories, and this function
    *does*.

    Parameters
    ----------
    feat_dir : str
        Path to feat-directory (output from fsl.FEAT node)
    task : str
        Name of task to give to the feat-directory (e.g. workingmemory,
        such that the name becomes workingmemory.feat)
    """

    import os.path as op
    import shutil

    new_name = op.basename(feat_dir).replace('run0.feat', '%s.feat' % task)
    dst = op.abspath(new_name)
    shutil.copytree(feat_dir, dst)

    return dst


Rename_feat_dir = Function(function=rename_feat_dir, input_names=['feat_dir', 'task'],
                           output_names=['feat_dir'])


def custom_level1design_feat(func_file, highres_file=None, session_info=None, output_dirname='firstlevel', 
                             contrasts='single-trial', smoothing=0, temp_deriv=False, registration='full', highpass=100,
                             slicetiming=None, motion_correction=None, bet=True, prewhitening=True, motion_regression=None,
                             thresholding='uncorrected', p_val=0.05, z_val=2.3, mask=None, hrf='doublegamma',
                             open_feat_html=False):
    """ Custom implementation of a FSL create-level1-design function.

    This function (which can be wrapped in a custom Nipype Function node) creates an FSL design.fsf
    file. This function is similar to the Nipype Level1Design node (interfaces.fsl.model) but allows
    for way more options to be set. 

    Parameters
    ----------
    func_file : str
        Path to functional file (4D) with timeseries data
    highres_file : str
        Path to file corresponding to high-resolution anatomical scan (should already be skull-stripped!).
        Only necessary if doing functional-highres-standard registration (i.e. registration = 'full');
        otherwise, set to None.
    session_info : Nipype Bunch-object
        Bunch-object (dict-like) with information about stimulus-related and nuisance regressors.
    output_dirname : str
        Name of output directory (.feat will be appended to it).
    contrasts : str, tuple, or list
        (List of) tuple(s) with defined contrasts. Should be formatted using the Nipype syntax:
        `(name_of_contrast, 'T', [cond_name_1, cond_name_2], [weight_1, weight_2])` for a t-contrast,
        or `(name_of_f_test, 'F', [contrast_1, contrast_2])` for F-tests.
    smoothing : float or int
        Smoothing kernel in FWHM (mm)
    temp_deriv : bool
        Whether to include temporal derivates of real EVs.
    registration : str
        Registration-scheme to apply. Currently supports three types: 'full', which registers
        the functional file to the high-res anatomical (using FLIRT BBR) and subsequent linear-
        non-linear registration to the MNI152 (2mm) standard brain (using FNIRT); another option
        is 'fmriprep', which only calculates a 3-parameter (translation only) transformation because
        output from the fmriprep-preprocessing-pipeline is already registered to MNI but is still in 
        native dimensions (i.e. EPI-space). Last option is 'none', which doesn't do any registration.
    highpass : int
        Length (in seconds) of FSL highpass filter to apply.
    slicetiming : str
        Whether to apply slice-time correction; options are 'up' (ascending), 'down' (descending),
        or 'no' (no slicetiming correction).
    motion_correction : bool
        Whether to apply motion-correction (MCFLIRT).
    bet : bool
        Whether to BET (skullstrip) the functional file.
    prewhitening : bool
        Whether to do prewhitening.
    motion_regression : str
        Whether to do motion-regression. Options: 'no' (no motion regression), 'yes' (standard 6 parameters motion
        regression), 'ext' (extended 24 parameter motion regression). 
    thresholding : str
        What type of thresholding to apply. Options: 'none', 'uncorrected', 'voxel', 'cluster'. 
    p_val : float
        What p-value to use in thresholding. 
    z_val : float  
        What minimum z-value to use in cluster-correction
    mask : str 
        File to use in pre-thresholding masking. Setting to None means no masking. 
    hrf : str
        What HRF-model to use. Default is 'doublegamma', but other options are: 'gamma',
        'gammabasisfunctions', 'gaussian'. 
    open_feat_html : bool
        Whether to automatically open HTML-progress report.

    Returns
    -------
    design_file : str
        The path to the created design.fsf file
    confound_txt_file : str
        Path to the created confounds.txt file
    ev_files : list
        List with paths to EV-text-files. 
    """
    import os.path as op
    import nibabel as nib
    from nipype.interfaces.fsl import Info
    import numpy as np
    import spynoza

    if isinstance(session_info, list):

        if len(session_info) == 1:
            session_info = session_info[0]

    if registration == 'full' and highres_file is None:
        raise ValueError("If you want to do a full registration, you need to specify a highres file!")

    if motion_correction in (0, False, 'yes') and motion_regression in ('yes', True, 1, 'ext', 2):
        raise ValueError("If you want to do motion-regression, make sure to turn on motion-correction!")

    if hrf == 'gammabasisfunctions' and temp_deriv:
        print("Cannot add temporal deriv when hrf = gammabasisfunctions; setting temp-deriv to False")
        temp_deriv = False

    n_orig_evs = len(session_info.conditions)
    if contrasts == 'single-trial':

        cons = []
        for i in range(n_orig_evs):
            con_values = np.zeros(len(session_info.conditions))
            con_values[i] = 1
            this_con = (session_info.conditions[i], 'T', session_info.conditions, con_values)
            cons.append(this_con)
        f_con = ('f_all', 'F', cons)
        cons.append(f_con)
        contrasts = cons
    elif isinstance(contrasts, list):  # assume nipype style contrasts
        for i, con in enumerate(contrasts):
            weights = np.zeros(n_orig_evs)
            this_i = 0
            for ii, ev in enumerate(session_info.conditions):
                if ev in con[2]:
                    weights[ii] = con[3][this_i]
                    this_i += 1
            contrasts[i] = (con[0], con[1], con[2], weights.tolist()) 

    t_contrasts = [con for con in contrasts if con[1] == 'T']
    f_contrasts = [con for con in contrasts if con[1] == 'F']
    n_con = len(t_contrasts)
    n_ftest = len(f_contrasts)
    n_real_evs = n_orig_evs

    if temp_deriv:
        n_real_evs *= 2
    elif hrf == 'gammabasisfunctions':
        n_real_evs *= 3  # ToDo: allow more than 3 basis funcs

    if temp_deriv:
        con_mode_old = 'real'
        con_mode = 'real'
    else:
        con_mode_old = 'orig'
        con_mode = 'orig'

    arg_dict = dict(temp_deriv={True: 1, 1: 1, False: 0, 0: 0},
                    
                    slicetiming={'no': 0, 0: 0, None: 0,
                                 'up': 1, 1: 1,
                                 'down': 2, 2: 2},
                    
                    motion_correction={True: 1, 1: 1, False: 0, 0: 0, None: 0},
                    
                    bet={True: 1, 1: 1, False: 0, 0: 0, None: 0},
                    
                    motion_regression={'no': 0, False: 0, None: 0,
                                       'yes': 1, True: 1, 1: 1,
                                       'ext': 2, 2: 2},
                    
                    thresholding={'none': 0, None: 0, 'no': 0, 0: 0,
                                  'uncorrected': 1, 'Uncorrected': 1, 1: 1,
                                  'voxel': 2, 'Voxel': 2, 2: 2,
                                  'cluster': 3, 'Cluster': 3, 3: 3},
                    
                    prewhitening={True: 1, 1: 1, False: 0, None: 0, 0: 0},
                    
                    hrf={'doublegamma': 3,
                         'none': 0, None: 0,
                         'gaussian': 1,
                         'gamma': 2,
                         'gammabasisfunctions': 4}, #,
                         #'sinebasisfunctions': 5,
                         #'firbasisfunctions': 6},

                    open_feat_html={True: 1, 1: 1,
                                    False: 0, 0: 0, None: 0}
                    )

    reg_dict = {'full': {'reghighres_yn': 1,
                         'reghighres_dof': 'BBR',
                         'regstandard_yn': 1,
                         'regstandard': Info.standard_image('MNI152_T1_2mm_brain.nii.gz'),
                         'regstandard_dof': 12,
                         'regstandard_nonlinear_yn': 1},
                
                'none': {'reghighres_yn': 0,
                         'regstandard_yn': 0},
                
                'fmriprep': {'reghighres_yn': 0,
                             'regstandard_yn': 1,
                             'regstandard_dof': 3,
                             'regstandard_nonlinear_yn': 0}
                }

    data_dir = op.join(op.dirname(spynoza.__file__), 'data')
    fsf_template = op.join(data_dir, 'fsf_templates', 'firstlevel_template.fsf')

    with open(fsf_template, 'r') as f:
        fsf_template = f.readlines()
        fsf_template = [txt.replace('\n', '') for txt in fsf_template if txt != '\n']
        fsf_template = [txt for txt in fsf_template if txt[0] != '#']  # remove commnts

    hdr = nib.load(func_file).header
    
    args = {'outputdir': "\"%s\"" % output_dirname,
            'tr': hdr['pixdim'][4],
            'npts': hdr['dim'][4],
            'smooth': smoothing,
            'deriv_yn': arg_dict['temp_deriv'][temp_deriv],
            'temphp_yn': 1 if highpass else 0,
            'paradigm_hp': highpass,
            'st': arg_dict['slicetiming'][slicetiming],
            'mc': arg_dict['motion_correction'][motion_correction],
            'bet_yn': arg_dict['bet'][bet],
            'prewhiten_yn': arg_dict['prewhitening'][prewhitening],
            'motionevs': arg_dict['motion_regression'][motion_regression],
            'threshmask': mask if mask is not None else "",
            'thresh': arg_dict['thresholding'][thresholding],
            'prob_thresh': p_val,
            'z_thresh': z_val,
            'evs_orig': n_orig_evs,
            'evs_real': n_real_evs,
            'ncon_orig': n_con,
            'ncon_real': n_con,
            'nftests_orig': n_ftest,
            'nftests_real': n_ftest,
            'con_mode_old': con_mode_old,
            'con_mode': con_mode,
            'featwatcher_yn': arg_dict['open_feat_html'][open_feat_html],
            'confoundevs': 1}

    args.update(reg_dict[registration])

    fsf_out = []

    # 4D AVW data or FEAT directory (1)
    fsf_out.append("set feat_files(1) \"%s\"" % func_file)

    confound_txt_file = op.join(op.abspath('confounds.txt'))
    if hasattr(session_info, 'regressors'):
        confounds = np.array(session_info.regressors).T
        np.savetxt(confound_txt_file, confounds, fmt=str('%.5f'), delimiter='\t')
        fsf_out.append('set confoundev_files(1) \"%s\"' % confound_txt_file)
    else:
        open(confound_txt_file, 'a').close()  # for compatibility issues
        fsf_out.append('set confoundev_files(1) \"\"')
    
    if highres_file is not None:

        fsf_template.append("set highres_files(1) \"%s\"" % highres_file)

    for line in fsf_template:

        if any(key in line for key in args.keys()):
            parts = [str(txt) for txt in line.split(' ') if txt]
            for key, value in args.items():
                if 'set fmri(%s)' % key in line:
                    parts[-1] = str(value)
                    break
            fsf_out.append(" ".join(parts))
        else:
            fsf_out.append(line)

    ev_files = []
    for i in range(n_orig_evs):

        fname = op.join(op.abspath(session_info.conditions[i] + '.txt'))
        info = np.vstack((session_info.onsets[i],
                          session_info.durations[i],
                          session_info.amplitudes[i])).T
        ev_files.append(fname)
        np.savetxt(fname, info, fmt=str('%.3f'), delimiter='\t')

        fsf_out.append('set fmri(evtitle%i) \"%s\"' % ((i + 1), session_info.conditions[i]))
        fsf_out.append('set fmri(shape%i) 3' % (i + 1))
        fsf_out.append('set fmri(convolve%i) %i' % ((i + 1), arg_dict['hrf'][hrf]))
        fsf_out.append('set fmri(convolve_phase%i) 0' % (i + 1))

        # Only relevant if hrf = 'gamma'
        fsf_out.append('set fmri(gammasigma%i) 3' % (i + 1))
        fsf_out.append('set fmri(gammadelay%i) 6' % (i + 1))

        # Only relevant if hrf = 'gammabasisfunctions'
        fsf_out.append('set fmri(basisfnum%i) 3' % (i + 1))
        fsf_out.append('set fmri(basisfwidth%i) 15' % (i + 1))
        fsf_out.append('set fmri(basisorth%i) 0' % (i + 1))

        fsf_out.append('set fmri(tempfilt_yn%i) %i' % ((i + 1), args['temphp_yn']))
        fsf_out.append('set fmri(deriv_yn%i) %i' % ((i + 1), args['deriv_yn']))
        fsf_out.append('set fmri(custom%i) %s' % ((i + 1), fname))
        
        for x in range(n_orig_evs + 1):
            fsf_out.append('set fmri(ortho%i.%i) 0' % ((i + 1), x))

    if contrasts and contrasts is not None:

        for i, contrast in enumerate(t_contrasts):
            cname, ctype, ccond, cweights = contrast
        
            fsf_out.append('set fmri(conpic_real.%i) 1' % (i + 1))
            fsf_out.append('set fmri(conname_real.%i) \"%s\"' % ((i + 1),
                                                                  cname))
            fsf_out.append('set fmri(conpic_orig.%i) 1' % (i + 1))
            fsf_out.append('set fmri(conname_orig.%i) \"%s\"' % ((i + 1),
                                                                 cname))

            for ii, weight in enumerate(cweights):
                fsf_out.append('set fmri(con_orig%i.%i) %.1f' % (i  + 1, ii + 1, float(weight)))

            ratio_orig_real = int(n_real_evs / n_orig_evs)
            real_weights = [[w] + [0] * (ratio_orig_real - 1) for w in cweights]
            real_weights = [item for sublist in real_weights for item in sublist]
            for ii, weight in enumerate(real_weights):
                fsf_out.append('set fmri(con_real%i.%i) %.1f' % (i  + 1, ii + 1, float(weight)))

        for i, contrast in enumerate(f_contrasts):

            for ii, tcon in enumerate(t_contrasts):
                to_set = 1 if tcon in contrast[2] else 0
                fsf_out.append('set fmri(ftest_orig%i.%i) %i' % (i + 1, ii + 1, to_set))
                fsf_out.append('set fmri(ftest_real%i.%i) %i' % (i + 1, ii + 1, to_set))

    design_file = op.join(op.abspath('design.fsf'))
    with open(design_file, 'w') as fsfout:
         print("Writing fsf to %s" % design_file)
         fsfout.write("\n".join(fsf_out))

    return design_file, confound_txt_file, ev_files


Custom_Level1design_Feat = Function(input_names=['func_file', 'highres_file', 'session_info',
                                                 'output_dirname', 'contrasts', 'smoothing',
                                                 'temp_deriv', 'registration', 'highpass',
                                                 'slicetiming', 'motion_correction', 'bet',
                                                 'prewhitening', 'motion_regression', 'thresholding',
                                                 'p_val', 'z_val', 'mask', 'hrf', 'open_feat_html'],
                                    output_names=['feat_dir', 'confound_file', 'ev_files'],
                                    function=custom_level1design_feat)    
