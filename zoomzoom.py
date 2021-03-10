"""Estimate speaking speed time series from zoom transcript.

"""
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


def remove_speaker(text):
    return text.split(":", 1)[1].strip()


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
        text = remove_speaker(caption.text)
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

    return beats_per_second


def zoom_timeseries(filename, window_size=5):

    beats_per_second = estimate_timing(filename)

    counter = 0
    ts = traces.TimeSeries(default=0)
    for caption in webvtt.read(filename):
        start, end = caption.start_in_seconds, caption.end_in_seconds
        text = remove_speaker(caption.text)
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
                ts[t] = counter
                counter += 1
            t += PAUSE_PROPORTION.get(stress_type, 1) / beats_per_second

    max_t = t

    new_ts = traces.TimeSeries(default=0)
    half_window = window_size
    t = -half_window - 1
    while t <= (max_t + 2 * half_window):
        n_syllables = ts[t + half_window] - ts[t - half_window]
        new_ts[t] = n_syllables
        t += 1

    result = []
    for t, v in new_ts.moving_average(0.1, half_window / 2):
        result.append((t, v))

    for i, (t, v) in enumerate(result):
        if v > 0:
            min_i = i - 1
            break

    for i in range(len(result) - 1, 0, -1):
        t, v = result[i]
        if v > 0:
            max_i = i + 2
            break

    result = result[min_i:max_i]
    min_t = result[0][0]

    result = [(t - min_t, v) for t, v in result]

    return result


if __name__ == "__main__":
    filename = sys.argv[1]
    for t, v in zoom_timeseries(filename, window_size):
        print(t, v)
