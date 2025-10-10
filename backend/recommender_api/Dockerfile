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
WORKDIR /recommender

ADD --chmod=755 https://astral.sh/uv/install.sh /install.sh
RUN /install.sh && rm /install.sh

COPY ./recommender_api/requirements.txt /recommender/requirements.txt
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
    unixodbc-dev && \
    rm -rf /var/lib/apt/lists/* && \
    ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

COPY --from=builder /opt/venv /opt/venv

WORKDIR /recommender
#COPY ./backend .
COPY ../alembic.ini /alembic.ini
COPY ../alembic /alembic
COPY scripts/healthcheck.sh /healthcheck.sh
RUN chmod +x /healthcheck.sh && \
    sed -i 's|script_location = alembic|script_location = /alembic|' /alembic.ini && \
    sed -i 's|prepend_sys_path = .|prepend_sys_path = /backend|' /alembic.ini

CMD ["python", "/recommender/start_api.py"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 CMD /healthcheck.sh