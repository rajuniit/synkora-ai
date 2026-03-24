# base image
FROM python:3.11-slim-bookworm AS base

WORKDIR /app/api

# Install uv
ENV UV_VERSION=0.5.11
RUN pip install --no-cache-dir uv==${UV_VERSION}


# packages stage - install dependencies
FROM base AS packages

# Install build dependencies including SAML/xmlsec requirements
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        make \
        libc-dev \
        libffi-dev \
        libpq-dev \
        libxml2-dev \
        libxmlsec1-dev \
        libxmlsec1-openssl \
        pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies using the lock file for reproducible builds
COPY pyproject.toml uv.lock ./
ENV UV_SYSTEM_PYTHON=1
RUN uv sync --frozen --no-dev


# production stage
FROM base AS production

ENV PYTHONUNBUFFERED=1
ENV EDITION=SELF_HOSTED
ENV DEPLOY_ENV=PRODUCTION

EXPOSE 5001

# Set timezone
ENV TZ=UTC

# Set UTF-8 locale
ENV LANG=en_US.UTF-8
ENV LC_ALL=en_US.UTF-8
ENV PYTHONIOENCODING=utf-8

WORKDIR /app/api

# Install runtime dependencies: Node.js (npx for MCP servers), SAML/xmlsec libs
# Playwright/Chromium now lives in synkora-scraper; those libs removed here.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        postgresql-client \
        libpq5 \
        libmagic1 \
        ca-certificates \
        git \
        openssh-client \
        # SAML/xmlsec runtime libraries
        libxml2 \
        libxmlsec1 \
        libxmlsec1-openssl \
        # Node.js (Debian bookworm ships Node 18 — sufficient for npx/MCP)
        nodejs \
        npm \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from packages stage
COPY --from=packages /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=packages /usr/local/bin /usr/local/bin

# Configure git identity for agent git operations (commit requires user.name + user.email)
# These are overridden at runtime by GIT_AGENT_EMAIL / GIT_AGENT_NAME env vars in git_commit_tools.py
RUN git config --system user.email "agent@localhost" && \
    git config --system user.name "AI Agent"

# Create non-root user
RUN useradd -m -u 1000 -s /bin/bash appuser

# Copy source code
COPY . /app/api/

# Copy and set entrypoint
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh && chown -R appuser:appuser /app

ARG COMMIT_SHA
ENV COMMIT_SHA=${COMMIT_SHA}

USER appuser

HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD curl -f http://localhost:5001/health || exit 1

ENTRYPOINT ["/bin/bash", "/entrypoint.sh"]
