"""Estimate speaking speed time series from zoom transcript.

"""
import pprint
import collections
import statistics
import string
import sys

import pronouncing
import traces
import webvtt

PAUSE_PROPORTION = {
    "3": 5,
    "4": 10,
}

ALIAS = {
    'Devanshi Verma': 'Devanshi Verma - Organizer',
    'Jane Zanzig | ( she / her) | IDEO': 'Jane Zanzig - Organizer( she / her)',
    'Kayla Schroeder': 'Kayla Schroeder - Organizer',
}


def split_speaker(raw):
    speaker, text = None, ''
    try:
        speaker, text = raw.split(":", 1)
    except ValueError:
        text = raw
    speaker = ALIAS.get(speaker, speaker)
    # speaker = 'all'
    return speaker, text.strip()


def stresses(word):
    clean = word.strip().lower().strip(string.punctuation)
    possible_stresses = pronouncing.stresses_for_word(clean)
    try:
        stresses = possible_stresses[0]
    except IndexError:
        stresses = "".join("1" for _ in range(count_syllables(clean)))
    return stresses


def count_syllables(word):
    syllable_count = 0
    vowels = "aeiouy"
    if word[0] in vowels:
        syllable_count += 1
    for index in range(1, len(word)):
        if word[index] in vowels and word[index - 1] not in vowels:
            syllable_count += 1
    if word.endswith("e"):
        syllable_count -= 1
    if word.endswith("le") and len(word) > 2 and word[-3] not in vowels:
        syllable_count += 1
    if syllable_count == 0:
        syllable_count += 1
    return syllable_count


def remove_outliers(distribution, q=1.5):
    quartiles = statistics.quantiles(distribution, n=4, method="inclusive")
    iqr = quartiles[-1] - quartiles[0]
    lower_whisker = quartiles[0] - q * iqr
    upper_whisker = quartiles[-1] + q * iqr
    return [i for i in distribution if lower_whisker <= i <= upper_whisker]


def estimate_timing(filename):
    pieces = []
    for caption in webvtt.read(filename):
        start, end = caption.start_in_seconds, caption.end_in_seconds
        speaker, text = split_speaker(caption.text)
        all_stresses = []
        for word in text.split():
            stress_string = stresses(word)
            if word.endswith(","):
                stress_string += "3"
            elif word.endswith("."):
                stress_string += "4"
            all_stresses.append(stress_string)
        stress_pattern = "".join(all_stresses)
        stress_pattern = stress_pattern.rstrip("4")
        dt = end - start
        n_beats = 0
        for stress_type in stress_pattern:
            n_beats += PAUSE_PROPORTION.get(stress_type, 1)
        pieces.append(n_beats / dt)

    tempo_distribution = remove_outliers(pieces)
    beats_per_second = max(tempo_distribution)

    return 6
    # return beats_per_second

def time_to_seconds(time):
    hour, minute, second = [int(float(_)) for _ in time.split(':')]
    return hour * 3600 + minute * 60 + second

def zoom_timeseries(filename, window_size=5, resolution=0.1, speaker_list=None):

    beats_per_second = estimate_timing(filename)
    print(f'beats per second: {beats_per_second}', file=sys.stderr)
    
    speaker_ts = traces.TimeSeries(default=None)
    for caption in webvtt.read(filename):
        start, end = caption.start_in_seconds, caption.end_in_seconds
        speaker, text = split_speaker(caption.text)
        if speaker is not None:
            speaker_ts.set(start, speaker, compact=True)

    unique_speakers = set(speaker for t, speaker in speaker_ts)
            
    counter, cumulative_ts = {}, {}
    for speaker in unique_speakers:
        counter[speaker] = 0
        cumulative_ts[speaker] = traces.TimeSeries(default=0)

    for caption in webvtt.read(filename):

        start, end = caption.start_in_seconds, caption.end_in_seconds
        _, text = split_speaker(caption.text)
        speaker = speaker_ts[start]
                
        all_stresses = []
        for word in text.split():
            stress_string = stresses(word)
            if word.endswith(","):
                stress_string += "3"
            elif word.endswith("."):
                stress_string += "4"
            all_stresses.append(stress_string)
            
        stress_pattern = "".join(all_stresses)
        stress_pattern = stress_pattern.rstrip("4")
        
        t = start
        for stress_type in stress_pattern:
            if stress_type in {"0", "1", "2"}:
                cumulative_ts[speaker][t] = counter[speaker]
                counter[speaker] += 1
            t += PAUSE_PROPORTION.get(stress_type, 1) / beats_per_second

        # print(speaker)
        # print(caption.text)
        # print(text)
        # print(stress_pattern)
        # print(syllable_counter[speaker])
        # print()
            
    pprint.pprint(counter)

    if speaker_list is None:
        speaker_list = list(sorted(cumulative_ts.keys()))
    
    result = []
    for speaker in speaker_list:

        ts = cumulative_ts[speaker]

        syllable_ts = traces.TimeSeries(default=0)
        half_window = window_size
        t = int(ts.first_key()) - (2 * half_window)
        while t <= (ts.last_key() + (2 * half_window)):
            n_syllables = ts[t + half_window] - ts[t - half_window]
            syllable_ts.set(t, n_syllables, compact=True)
            t += 1

        result.append((
            speaker,
            syllable_ts.moving_average(0.1, half_window / 2),
        ))

    return result


if __name__ == "__main__":
    filename = sys.argv[1]
    window_size = 5
    ts, t_end = zoom_timeseries(filename, window_size, 1)
    for t, v in ts:
        print(t, v)
