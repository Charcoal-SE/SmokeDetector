import sys
import json

array = json.load(sys.stdin)["items"]

for user in array:
    if user["question_count"] == 0:
        print user["link"]
