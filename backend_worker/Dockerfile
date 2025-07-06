FROM python:3.13-slim AS builder
RUN echo "deb http://ftp.fr.debian.org/debian bookworm main" > /etc/apt/sources.list && \
    apt-get update && apt-get install -y --no-install-recommends \
    apt-transport-https \
    build-essential \
    cargo \
    curl \
    libpq-dev \
    rustc \
    unixodbc \
    unixodbc-dev \
    && rm -rf /var/lib/apt/lists/*

ENV PATH="/opt/venv/bin:$PATH"
WORKDIR /backend_worker

ADD --chmod=755 https://astral.sh/uv/install.sh /install.sh
RUN /install.sh && rm /install.sh

COPY ./backend_worker/requirements.txt /backend_worker/requirements.txt
RUN /root/.local/bin/uv venv /opt/venv && \
    /root/.local/bin/uv pip install --no-cache-dir -r requirements.txt

FROM python:3.13-slim AS runner

ARG LOCALE_LANGUAGE=en_US
ARG ENV_LOCALE_LANGUAGE
ENV LOCALE_LANGUAGE=${ENV_LOCALE_LANGUAGE:-${LOCALE_LANGUAGE}}
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

ARG TZ=UTC
ARG ENV_TZ
ENV TZ=${ENV_TZ:-${TZ}}

RUN echo "deb http://ftp.fr.debian.org/debian bookworm main" > /etc/apt/sources.list && \
    apt-get update && apt-get install -y --no-install-recommends \
    apt-transport-https \
    curl \
    gcc \
    g++ \
    libpq-dev \
    nfs-common \
    cifs-utils \
    unixodbc \
    unixodbc-dev \
    locales && \
    # Générer la locale UTF-8
    sed -i -e 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen && \
    dpkg-reconfigure --frontend=noninteractive locales && \
    update-locale LANG=${LANG} && \
    # Nettoyage
    rm -rf /var/lib/apt/lists/* && \
    ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

COPY --from=builder /opt/venv /opt/venv

WORKDIR /backend_worker
CMD ["celery", "-A", "backend_worker.celery_app", "worker", "--loglevel=debug", "-E"]

