FROM ubuntu

RUN DEBIAN_FRONTEND=noninteractive && \
    apt -y update && \
    apt install -y build-essential \
        python3 python3-dev python3-pip python3-venv git ca-certificates && \
    adduser --disabled-password --force-badname SmokeDetector \
        --gecos SmokeDetector && \
    su - SmokeDetector sh -c '\
        git clone https://github.com/Charcoal-SE/SmokeDetector.git && \
        cd SmokeDetector && \
        python3 -m venv venv && \
        . ./venv/bin/activate && \
        pip3 install -r user_requirements.txt --upgrade' && \
    pip3 install -r ~SmokeDetector/SmokeDetector/requirements.txt --upgrade && \
    apt autoremove -y --purge build-essential python3-dev && \
    apt clean && \
    rm -rf /root/* /var/lib/apt/lists/* /tmp/* /var/tmp/*

CMD ["su", "-", "SmokeDetector"]
