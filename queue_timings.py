#!/usr/bin/env python3
# coding=utf-8
# queue_timings.py
# Analysis script for bodyfetcher queue timings. Call from the command line using Python 3 in the pickles directory.

import os.path
# noinspection PyPep8Naming
import pickle
import warnings
import math


def main():
    queue_data = {}
    found_timing = False
    if os.path.isfile("bodyfetcherQueueTimings.p"):
        warnings.warn("Timing data in pickle format is deprecated; use the plain text format instead.",
                      DeprecationWarning)
        found_timing = True
        try:
            with open("bodyfetcherQueueTimings.p", "rb") as f:
                queue_data = pickle.load(f)
        except EOFError:
            print("Hit EOFError while reading file. Smokey handles this by deleting the file.")
            resp = input("Delete? (y/n)").lower()
            if resp == "y":
                os.remove("bodyfetcherQueueTimings.p")
    if os.path.isfile("bodyfetcherQueueTimings.txt"):
        found_timing = True
        with open("bodyfetcherQueueTimings.txt", mode="r", encoding="utf-8") as stat_file:
            for stat_line in stat_file:
                site, time_str = stat_line.split(" ", 1)
                time_in_queue = float(time_str)
                if site in queue_data:
                    queue_data[site].append(time_in_queue)
                else:
                    queue_data[site] = [time_in_queue]

    if found_timing:
        print("SITE,MIN,MAX,AVG,Q1,MEDIAN,Q3,STDDEV,COUNT,98P_MIN,98P_MAX")
        # noinspection PyUnboundLocalVariable
        for site, times in queue_data.items():
            sorted_times = sorted(times)
            median = sorted_times[int(len(sorted_times) * 0.5)]
            q1 = sorted_times[int(len(sorted_times) * 0.25)]
            q3 = sorted_times[int(len(sorted_times) * 0.75)]

            mean = sum(times) / len(times)
            diff_sqr = [(x - mean) ** 2 for x in times]
            stddev = math.sqrt(sum(diff_sqr) / len(diff_sqr))

            min98 = max(mean - 2 * stddev, min(times))
            max98 = min(mean + 2 * stddev, max(times))

            print("{0},{1},{2},{3},{4},{5},{6},{7},{8},{9},{10}"
                  .format(site.split(".")[0], min(times), max(times), mean, q1, median,
                          q3, stddev, len(times), min98, max98))

    else:
        print("bodyfetcherQueueTimings.txt doesn't exist. No data to analyse.")


if __name__ == "__main__":
    main()
