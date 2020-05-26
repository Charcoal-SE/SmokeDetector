#!/usr/bin/env python3
# coding=utf-8
# queue_timings.py
# Analysis script for bodyfetcher queue timings. Call from the command line using Python 3.

import os.path
# noinspection PyPep8Naming
import math


def main():
    queue_data = {}
    if os.path.isfile("bodyfetcherQueueTimings.txt"):
        with open("bodyfetcherQueueTimings.txt", mode="r", encoding="utf-8") as stat_file:
            for stat_line in stat_file:
                time_str, site_str = stat_line.split(" ", 1)
                site = site_str[:-1]
                time_in_queue = float(time_str)
                if site in queue_data:
                    queue_data[site].append(time_in_queue)
                else:
                    queue_data[site] = [time_in_queue]

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
