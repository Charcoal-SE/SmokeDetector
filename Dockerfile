# Keep this Python image version manually maintained
FROM python:3.7-stretch

RUN adduser --disabled-password --force-badname smokey --gecos smokey && \
    su --login smokey sh -c '\
        git clone --depth=50 https://github.com/Charcoal-SE/SmokeDetector.git && \
        cd SmokeDetector && \
        pip3 install --user -r user_requirements.txt --upgrade' && \
    pip3 install -r ~smokey/SmokeDetector/requirements.txt --upgrade && \
    rm -rf /root/* /var/lib/apt/lists/* /tmp/* /var/tmp/*

CMD ["su", "--login", "smokey", "-c", "/home/smokey/SmokeDetector/docker-startup.sh"]
