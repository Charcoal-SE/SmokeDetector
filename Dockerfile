FROM ubuntu
MAINTAINER CaffeineAddiction

RUN apt update && \
    apt install build-essential python2.7 python-dev git wget -y && \
    wget https://bootstrap.pypa.io/get-pip.py && \
    python2.7 get-pip.py && \
    cd ~ && \
    env GIT_SSL_NO_VERIFY=true git clone https://github.com/Charcoal-SE/SmokeDetector.git && \
    cd SmokeDetector && \
    git submodule init && \
    git submodule update && \
    pip install -r requirements.txt --upgrade

RUN apt remove -y --purge build-essential python-dev git wget && \
    apt clean && \
    rm -rf /root/* /var/lib/apt/lists/* /tmp/* /var/tmp/*


CMD ["/bin/bash"]
