FROM python:3
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN adduser --disabled-password smokey --gecos smokey && \
    su --login smokey sh -c '\
        git clone --depth=1 --no-single-branch https://github.com/Charcoal-SE/SmokeDetector.git && \
        cd SmokeDetector && \
        uv sync' && \
    rm -rf /root/* /var/lib/apt/lists/* /tmp/* /var/tmp/*

CMD ["su", "--login", "smokey", "-c", "/home/smokey/SmokeDetector/docker-startup.sh standby"]
