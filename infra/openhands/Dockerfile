FROM docker:29-cli AS dockercli

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends bash git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=dockercli /usr/local/bin/docker /usr/local/bin/docker
COPY --from=dockercli /usr/local/libexec/docker /usr/local/libexec/docker

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir openhands

WORKDIR /workspace

ENTRYPOINT ["/bin/bash", "-lc"]
CMD ["openhands --help"]
