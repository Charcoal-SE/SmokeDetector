# queue_timings.py
# Analysis script for bodyfetcher queue timings. Call from the command line using Python 3.

import os.path
import cPickle as pickle
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

        for site, times in queue_data.iteritems():
            sorted_times = sorted(times)
            median_i = len(sorted_times) / 2
            if isinstance(median_i, (int, long)):
                median = sorted_times[median_i - 1]
            else:
                median = (sorted_times[int(math.floor(median_i) - 1)] +
                          sorted_times[int(math.ceil(median_i) - 1)]) / 2

            left = sorted_times[0:int(math.floor(median_i))]
            right = sorted_times[int(math.floor(median_i)):-1]

            q1_i = len(left) / 2
            if isinstance(q1_i, (int, long)):
                q1 = left[q1_i - 1]
            else:
                q1 = (left[int(math.floor(q1_i) - 1)] + left[int(math.ceil(q1_i) - 1)]) / 2

            q3_i = len(right) / 2
            if isinstance(q3_i, (int, long)):
                q3 = right[q3_i - 1]
            else:
                q3 = (right[int(math.floor(q3_i) - 1)] + right[int(math.ceil(q3_i) - 1)]) / 2

            print("{0}: min {1}, max {2}, avg {3}, q1 {4}, q3 {5}".format(site.split(".")[0],
                                                                          min(times),
                                                                          max(times),
                                                                          sum(times) / len(times),
                                                                          q1, q3))

    else:
        print("bodyfetcherQueueTimings.p doesn't exist. No data to analyse.")


if __name__ == "__main__":
    main()
