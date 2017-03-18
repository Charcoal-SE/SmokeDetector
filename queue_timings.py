# queue_timings.py
# Analysis script for bodyfetcher queue timings. Call from the command line using Python 3 (or Python 2, thanks to
# the compatibility code below).

import os.path
import platform
# Handle both Python 2 and Python 3 compatibility with Pickle and cPickle
if int(platform.python_version_tuple()[0]) == 2:
    import cPickle as pickle
elif int(platform.python_version_tuple()[0]) == 3:
    import pickle
else:
    raise EnvironmentError("Invalid or Incompatible Python Version: %s" % platform.python_version())


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
            return  # If we don't return, we run into an error in the for loop below.

        for site, times in queue_data.iteritems():
            print("{0}: min {1}, max {2}, avg {3}".format(site.split(".")[0], min(times), max(times),
                                                          sum(times) / len(times)))

    else:
        print("bodyfetcherQueueTimings.p doesn't exist. No data to analyse.")


if __name__ == "__main__":
    main()
