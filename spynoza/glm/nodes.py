from nipype.interfaces.utility import Function


def events_file_to_bunch(in_file):
    import pandas as pd
    from nipype.interfaces.base import Bunch

    events = pd.read_csv(in_file, sep=str('\t'))
    conditions = sorted(events['trail_type'].unique())
    onsets = [events['onset'][events['trail_type'] == tt].tolist() for tt in conditions]
    durations = [events['duration'][events['trail_type'] == tt].tolist() for tt in conditions]
    amplitudes = [events['weight'][events['trail_type'] == tt].tolist() for tt in conditions]
    print(onsets)
    bunch = Bunch(conditions=conditions,
                  onsets=onsets,
                  durations=durations,
                  amplitudes=amplitudes)
    return bunch

Events_file_to_bunch = Function(function=events_file_to_bunch,
                                input_names=['in_file'],
                                output_names=['bunch'])
