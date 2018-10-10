#!/usr/bin/env python3
# queue_timings.py
# Analysis script for bodyfetcher queue timings. Call from the command line using Python 3.

import os.path
# noinspection PyPep8Naming
import pickle
import math


def main():
    if os.path.isfile("bodyfetcherQueueTimings.p"):
        try:
            with open("bodyfetcherQueueTimings.p", "rb") as f:
                queue_data = pickle.load(f)
        except EOFError:
            print("Hit EOFError while reading file. Smokey handles this by deleting the file.")
            resp = input("Delete? (y/n)").lower()
            if resp == "y":
                os.remove("bodyfetcherQueueTimings.p")

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
        print("bodyfetcherQueueTimings.p doesn't exist. No data to analyse.")


if __name__ == "__main__":
    main()
