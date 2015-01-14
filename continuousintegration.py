import socket
import requests
import re
from globalvars import GlobalVars
import datetime

def watchCi():
    HOST = ''
    PORT = 49494

    s=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print "CI Socket Created"

    try:
        s.bind((HOST, PORT))
    except socket.error as msg:
        print 'Bind Failed. Error code: ' + str(msg[0])
        return

    s.listen(10)
    print 'listening for ci changes'

    while 1:
        conn, addr = s.accept()
        addr_host = socket.gethostbyaddr(addr[0])[0]
        is_circleci = True if re.compile(r"ec2-\d{1,3}-\d{1,3}-\d{1,3}-\d{1,3}.compute-1.amazonaws.com").search(addr_host) else False
        print 'Received request from ' + addr[0] + " ; " + "verified as CircleCI" if is_circleci else "NOT verified as CircleCI!"
        if not is_circleci:
            continue
        r=requests.get('https://api.github.com/repos/Charcoal-SE/SmokeDetector/git/refs/heads/master')
        latest_sha = r.json()["object"]["sha"]
        r = requests.get('https://api.github.com/repos/Charcoal-SE/SmokeDetector/commits/' + latest_sha + '/statuses')
        for status in r.json():
            state = status["state"]
            if state == "success":
                if datetime.datetime.strptime(status["updated_at"], '%Y-%m-%dT%H:%M:%SZ') > datetime.datetime.now()-datetime.timedelta(seconds=10):
                    GlobalVars.charcoal_hq.send_message("CI build passed. Ready to pull!")
                    return
            elif state == "error" or state == "failure":
                if datetime.datetime.strptime(status["updated_at"], '%Y-%m-%dT%H:%M:%SZ') > datetime.datetime.now()-datetime.timedelta(seconds=10):
                    GlobalVars.charcoal_hq.send_message("CI build failed, *someone* (prolly Undo) borked something!")
                    return
        s.close()
