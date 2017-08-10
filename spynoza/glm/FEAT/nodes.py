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


def custom_level1design_feat(func_file, highres_file=None, output_dirname='firstlevel', session_info=None,
                             contrasts='single-trial', smoothing=0.0, temp_deriv=False, registration='fmriprep', highpass=0,
                             slicetiming=0, motion_correction=0, bet=0, prewhitening=0, motion_regression='no',
                             thresholding='uncorrected', p_val=0.05, z_val=2.3, mask=None, hrf='doublegamma'):
    import os.path as op
    import nibabel as nib
    from nipype.interfaces.fsl import Info
    import numpy as np

    if registration == 'full' and highres_file is None:
        raise ValueError("If you want to do a full registration, you need to specify a highres file!")

    n_evs = len(session_info.conditions)

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
                         'firbasisfunctions': 6}
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

    data_dir = op.join(op.dirname(op.dirname(op.dirname(__file__))), 'data')
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
            'evs_orig': n_evs,
            'evs_real': n_evs,
            **reg_dict[registration]}

    fsf_out = []

    # 4D AVW data or FEAT directory (1)
    fsf_out.append("set feat_files(1) \"%s\"" % func_file)
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
    
    if contrasts == 'single-trial':
    
        for i in range(n_evs):

            fname = op.join(op.abspath(session_info.conditions[i] + '.txt'))
            info = np.vstack((session_info.onsets[i],
                              session_info.durations[i],
                              session_info.amplitudes[i])).T
            np.savetxt(fname, info, fmt='%.3f', delimiter='\t')

            fsf_out.append('set fmri(evtitle%i) \"%s\"' % ((i + 1), session_info.conditions[i]))
            fsf_out.append('set fmri(shape%i) 3' % (i + 1))
            fsf_out.append('set fmri(convolve%i) %i' % ((i + 1), arg_dict['hrf'][hrf]))
            fsf_out.append('set fmri(convolve_phase%i) 0' % (i + 1))
            fsf_out.append('set fmri(tempfilt_yn%i) %i' % ((i + 1), args['temphp_yn']))
            fsf_out.append('set fmri(deriv_yn%i) %i' % ((i + 1), args['deriv_yn']))
            fsf_out.append('set fmri(custom%i) %s' % ((i + 1), fname))
        
            for x in range(n_evs + 1):
                fsf_out.append('set fmri(ortho%i.%i) 0' % ((i + 1), x))
        
            fsf_out.append('set fmri(conpic_real.%i) 1' % (i + 1))
            fsf_out.append('set fmri(conname_real.%i) \"%s\"' % ((i + 1),
                                                                 session_info.conditions[i]))
            fsf_out.append('set fmri(conpic_orig.%i) 1' % (i + 1))
            fsf_out.append('set fmri(conname_orig.%i) \"%s\"' % ((i + 1),
                                                                 session_info.conditions[i]))
            for x in range(n_evs):
                to_set = "1" if (x + 1) == (i + 1) else "0"

                fsf_out.append('set fmri(con_real%i.%i) %s' % ((i + 1), (x + 1), to_set))
                fsf_out.append('set fmri(con_orig%i.%i) %s' % ((i + 1), (x + 1), to_set))

            fsf_out.append('set fmri(ftest_real1.%i) 1' % (i + 1))
            fsf_out.append('set fmri(ftest_orig1.%i) 1' % (i + 1))

        for x in range(n_evs):

            for y in range(n_evs):

                if (x + 1) == (y + 1):
                    continue

                fsf_out.append('set fmri(conmask%i_%i) 0' % ((x + 1),
                                                             (y + 1)))
    elif contrasts is not None:

        for i, contrast in enumerate(contrasts):

            cname, ctype, ccond, cweights = contrasts
            fsf_out.append('set fmri(conpic_real.%i) 1' % (i + 1))
            fsf_out.append('set fmri(conname_real.%i) \"%s\"' % ((i + 1),
                                                                  cname))
            fsf_out.append('set fmri(conpic_orig.%i) 1' % (i + 1))
            fsf_out.append('set fmri(conname_orig.%i) \"%s\"' % ((i + 1),
                                                                 cname))
            
            

        pass

    to_write = op.join(op.abspath('design.fsf'))
    with open(to_write, 'w') as fsfout:
         print("Writing fsf to %s" % to_write)
         fsfout.write("\n".join(fsf_out))

if __name__ == '__main__':
    import joblib
    wm_bunch = joblib.load('/media/lukas/goliath/PipelineComparison/testset_pipelines/preproc/fmriprep/sub-0020/func/wm_bunch.jl')
    custom_level1design_feat("/media/lukas/goliath/PipelineComparison/testset_pipelines/preproc/fmriprep/sub-0020/func/sub-0020_task-workingmemory_acq-sequential_bold_space-MNI152NLin2009cAsym_preproc.nii.gz",
                             highres_file="/media/lukas/goliath/PipelineComparison/testset_pipelines/preproc/fmriprep/sub-0020/anat/sub-0020_T1w_preproc.nii.gz", session_info=wm_bunch)
    