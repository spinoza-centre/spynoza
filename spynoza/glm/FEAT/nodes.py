from nipype.interfaces.utility import Function


def rename_feat_dir(feat_dir, task):
    """ Renames the FEAT directory from fsl.FEAT.

    Mimicks nipype.utility.Rename, but Rename doesn't
    work for directories (it seems ...), and this function
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


def custom_level1design_feat(func_file, highres_file=None, session_info=None, output_dirname='firstlevel_hp100_smooth5_pw_stc_deriv_gbf', 
                             contrasts='single-trial', smoothing=5, temp_deriv=True, registration='fmriprep', highpass=100,
                             slicetiming='up', motion_correction=0, bet=True, prewhitening=1, motion_regression='no',
                             thresholding='uncorrected', p_val=0.05, z_val=2.3, mask=None, hrf='gamma',
                             open_feat_html=True):
    
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
        n_con = len(session_info.conditions)
        n_ftest = 1
    else:
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
                    
                    motion_correction={True: 1, 1: 1, False: 0, 0: 0},
                    
                    bet={True: 1, 1: 1, False: 0, 0: 0},
                    
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
                         'gammabasisfunctions': 4,
                         'sinebasisfunctions': 5,
                         'firbasisfunctions': 6},

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
    
    args = {'outputdir': "\"%s\"" % op.join(op.abspath(output_dirname)),
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

    # Add confound (ToDo: do nothing if there are no regressors)
    confounds = np.array(session_info.regressors).T
    confound_txt_file = op.join(op.abspath('confounds.txt'))
    
    np.savetxt(confound_txt_file, confounds, fmt=str('%.5f'), delimiter='\t')
    fsf_out.append('set confoundev_files(1) \"%s\"' % confound_txt_file)

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

    if contrasts == 'single-trial':
    
        for i in range(n_orig_evs):
            fsf_out.append('set fmri(conpic_real.%i) 1' % (i + 1))
            fsf_out.append('set fmri(conname_real.%i) \"%s\"' % ((i + 1),
                                                                 session_info.conditions[i]))
            fsf_out.append('set fmri(conpic_orig.%i) 1' % (i + 1))
            fsf_out.append('set fmri(conname_orig.%i) \"%s\"' % ((i + 1),
                                                                 session_info.conditions[i]))
            for x in range(n_orig_evs):
                to_set = "1" if (x + 1) == (i + 1) else "0"

                fsf_out.append('set fmri(con_orig%i.%i) %s' % ((i + 1), (x + 1), to_set))

            for x in range(n_real_evs):
                to_set = "1" if x == i else "0"
                fsf_out.append('set fmri(con_real%i.%i) %s' % ((i + 1), (x + 1), to_set))

            fsf_out.append('set fmri(ftest_real1.%i) 1' % (i + 1))
            fsf_out.append('set fmri(ftest_orig1.%i) 1' % (i + 1))

        for x in range(n_orig_evs):

            for y in range(n_orig_evs):

                if (x + 1) == (y + 1):
                    continue

                fsf_out.append('set fmri(conmask%i_%i) 0' % ((x + 1),
                                                             (y + 1)))
    
    elif contrasts and contrasts is not None:

        for i, contrast in enumerate(t_contrasts):
            cname, ctype, ccond, cweights = contrast
        
            fsf_out.append('set fmri(conpic_real.%i) 1' % (i + 1))
            fsf_out.append('set fmri(conname_real.%i) \"%s\"' % ((i + 1),
                                                                  cname))
            fsf_out.append('set fmri(conpic_orig.%i) 1' % (i + 1))
            fsf_out.append('set fmri(conname_orig.%i) \"%s\"' % ((i + 1),
                                                                 cname))

            for ii, weight in enumerate(cweights):
                fsf_out.append('set fmri(con_orig.%i.%i) %.1f' % (i  + 1, ii + 1, float(weight)))

            ratio_orig_real = int(n_real_evs / n_orig_evs)
            real_weights = [[w] + [0] * (ratio_orig_real - 1) for w in cweights]
            real_weights = [item for sublist in real_weights for item in sublist]
            for ii, weight in enumerate(real_weights):
                fsf_out.append('set fmri(con_real.%i.%i) %.1f' % (i  + 1, ii + 1, float(weight)))

        for i, contrast in enumerate(f_contrasts):

            for ii, tcon in enumerate(t_contrasts):
                to_set = 1 if tcon in contrast[2] else 0
                fsf_out.append('set fmri(ftest_orig%i.%i) %i' % (i + 1, ii + 1, to_set))
                fsf_out.append('set fmri(ftest_real%i.%i) %i' % (i + 1, ii + 1, to_set))

    to_write = op.join(op.abspath('design.fsf'))
    with open(to_write, 'w') as fsfout:
         print("Writing fsf to %s" % to_write)
         fsfout.write("\n".join(fsf_out))

    return to_write, confound_txt_file, ev_files


Custom_Level1design_Feat = Function(input_names=['func_file', 'highres_file', 'session_info',
                                                 'output_dirname', 'contrasts', 'smoothing',
                                                 'temp_deriv', 'registration', 'highpass',
                                                 'slicetiming', 'motion_correction', 'bet',
                                                 'prewhitening', 'motion_regression', 'thresholding',
                                                 'p_val', 'z_val', 'mask', 'hrf', 'open_feat_html'],
                                    output_names=['feat_dir', 'confound_file', 'ev_files'],
                                    function=custom_level1design_feat)    