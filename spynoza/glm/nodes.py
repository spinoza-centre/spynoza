from nipype.interfaces.utility import Function


def events_file_to_bunch(in_file, single_trial=False, sort_by_onset=False,
                         exclude=None):
    import pandas as pd
    from nipype.interfaces.base import Bunch

    events = pd.read_csv(in_file, sep=str('\t'))
    
    if exclude is not None:  # not tested
        events.drop(exclude, axis=1, inplace=True)

    if single_trial:

        if sort_by_onset:
            events = events.sort_values(by='onset')

        conditions = [[e] for e in events['trial_type'].tolist()] 
        onsets = [[e] for e in events['onset'].tolist()]
        durations = [[e] for e in events['duration'].tolist()]
        amplitudes = [[e] for e in events['weight'].tolist()]
    else:
        conditions = sorted(events['trial_type'].unique())
        onsets = [events['onset'][events['trial_type'] == tt].tolist() for tt in conditions]
        durations = [events['duration'][events['trial_type'] == tt].tolist() for tt in conditions]
        amplitudes = [events['weight'][events['trial_type'] == tt].tolist() for tt in conditions]

    bunch = Bunch(conditions=conditions,
                  onsets=onsets,
                  durations=durations,
                  amplitudes=amplitudes)
    return bunch

Events_file_to_bunch = Function(function=events_file_to_bunch,
                                input_names=['in_file', 'single_trial', 'sort_by_onset', 'exclude'],
                                output_names=['subject_info'])


def load_confounds(in_file, which_confounds, extend_motion_pars=False):
    import pandas as pd
    import numpy as np
    from nipype.interfaces.base import Bunch

    if isinstance(which_confounds, str):
        which_confounds = [which_confounds]

    df = pd.read_csv(in_file, sep=str('\t'))

    if extend_motion_pars:

        if 'RotX' in df.columns.values:  # fmriprep terminology
            col_names = ['X', 'Y', 'Z', 'RotX', 'RotY', 'RotZ']
        else:  # FSL terminology
            col_names = ['X', 'Y', 'Z', 'Rot_X', 'Rot_Y', 'Rot_Z']

        moco_pars = np.array(df[col_names])
        moco_sq = moco_pars ** 2
        moco_diff = np.diff(np.vstack((np.ones((1, 6)), moco_pars)), axis=0)
        moco_diff_sq = moco_diff ** 2
        ext_moco_pars = np.hstack((moco_sq, moco_diff, moco_diff_sq))
        new_names = [c + '_sq' for c in col_names]
        new_names.extend([c + '_dt' for c in col_names])
        new_names.extend([c + '_dt_sq' for c in col_names])
        moco_ext = pd.DataFrame(ext_moco_pars, columns=new_names)
        # We're going to assume that if you want to extend the motion params,
        # you want to regress them out ...
        which_confounds.extend(new_names)
        df = pd.concat((df, moco_ext), axis=1)

    subdf = pd.DataFrame(df[which_confounds])
    regressor_names = subdf.columns.values
    regressors = [subdf[col].tolist() for col in subdf.columns]
    return regressor_names, regressors


Load_confounds = Function(function=load_confounds,
                          input_names=['in_file', 'which_confounds', 'extend_motion_pars'],
                          output_names=['regressor_names', 'regressors'])


def combine_events_and_confounds(subject_info, confound_names, confounds):
    
    subject_info.update(regressors=confounds, regressor_names=confound_names)
    return subject_info


Combine_events_and_confounds = Function(function=combine_events_and_confounds,
                                        input_names=['subject_info', 'confound_names', 'confounds'],
                                        output_names=['subject_info'])
