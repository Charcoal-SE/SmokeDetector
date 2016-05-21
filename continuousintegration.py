import socket
import requests
import re
import os
from globalvars import GlobalVars
import datetime
import time
import random


def watch_ci():
    HOST = ''
    PORT = 49494

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print "CI Socket Created"

    try:
        s.bind((HOST, PORT))
    except socket.error as msg:
        print 'Bind Failed. Error code: ' + str(msg[0])
        return

    s.listen(10)
    print 'listening for CI changes'

    while True:
        conn, addr = s.accept()

        addr_host = socket.gethostbyaddr(addr[0])[0]
        is_circleci = True if re.compile(r"ec2-\d{1,3}-\d{1,3}-\d{1,3}-\d{1,3}.compute-1.amazonaws.com").search(addr_host) else False
        print 'Received request from ' + addr[0] + " ; " + "verified as CircleCI" if is_circleci else "NOT verified as CircleCI!"
        if not is_circleci:
            conn.close()
            continue
        conn.send('HTTP/1.1 200 OK\n' +
                  'Content-Type: text/plain\n'
                  'Content-Length: 2\n' +
                  '\nOK\n')
        conn.close()
        request = requests.get(
            'https://api.github.com/repos/Charcoal-SE/SmokeDetector/git/refs/heads/master'
        )
        latest_sha = request.json()["object"]["sha"]
        print latest_sha
        request = requests.get(
            'https://api.github.com/repos/Charcoal-SE/SmokeDetector/commits/{0}/statuses'.format(
                latest_sha
            )
        )
        for status in request.json():
            state = status["state"]
            target_url = status["target_url"]

            ci_platform = ""

            if status["context"] == "ci/circleci":
                ci_platform = "Circle"
            elif status["context"] == "continuous-integration/travis-ci/push":
                ci_platform = "Travis"
            else:
                ci_platform = "some unrecognized test service"

            print state
            if state == "success":
                time_to_test = datetime.datetime.now() - datetime.timedelta(seconds=60)
                if datetime.datetime.strptime(status["updated_at"], '%Y-%m-%dT%H:%M:%SZ') > time_to_test:

                    request = requests.get('https://api.github.com/repos/Charcoal-SE/SmokeDetector/commits/' + latest_sha)
                    commit_message = r.json()["commit"]["message"]
                    print commit_message
                    if "autopull" in commit_message:
                        GlobalVars.charcoal_hq.send_message("[CI build passed]({}) on {}. Commit message contains 'autopull', pulling...".format(target_url, ci_platform))
                        time.sleep(2)
                        os._exit(3)
                    else:
                        GlobalVars.charcoal_hq.send_message("[CI build passed]({}) on {}. Ready to pull!".format(target_url, ci_platform))

                    continue
            elif state == "error" or state == "failure":
                if datetime.datetime.strptime(status["updated_at"], '%Y-%m-%dT%H:%M:%SZ') > datetime.datetime.now() - datetime.timedelta(seconds=10):
                    GlobalVars.charcoal_hq.send_message("[CI build failed]({})".format(target_url) + ", *someone* (prolly " + random.choice(["Undo", "Manish", "ProgramFOX", "hichris", "Normal"]) + ") borked something!")
                    continue
    s.close()
