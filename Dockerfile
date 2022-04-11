# Keep this Python image version manually maintained
FROM python:3.10

RUN adduser --disabled-password smokey --gecos smokey && \
    su --login smokey sh -c '\
        git clone --depth=1 --no-single-branch https://github.com/Charcoal-SE/SmokeDetector.git && \
        cd SmokeDetector && \
        pip3 install --user -r user_requirements.txt --upgrade' && \
    pip3 install -r ~smokey/SmokeDetector/requirements.txt --upgrade && \
    rm -rf /root/* /var/lib/apt/lists/* /tmp/* /var/tmp/*

CMD ["su", "--login", "smokey", "-c", "/home/smokey/SmokeDetector/docker-startup.sh standby"]
