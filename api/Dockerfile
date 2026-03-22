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

# Install Python dependencies system-wide
COPY pyproject.toml uv.lock ./
RUN uv pip install --system --no-cache -r pyproject.toml


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

# Install runtime dependencies including Node.js for MCP stdio servers, GitHub CLI, SAML/xmlsec, and Playwright dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        postgresql-client \
        libpq5 \
        libmagic1 \
        ca-certificates \
        gnupg \
        git \
        openssh-client \
        # SAML/xmlsec runtime libraries
        libxml2 \
        libxmlsec1 \
        libxmlsec1-openssl \
        # Playwright/Chromium dependencies
        libnss3 \
        libnspr4 \
        libatk1.0-0 \
        libatk-bridge2.0-0 \
        libcups2 \
        libdrm2 \
        libdbus-1-3 \
        libxkbcommon0 \
        libxcomposite1 \
        libxdamage1 \
        libxfixes3 \
        libxrandr2 \
        libgbm1 \
        libpango-1.0-0 \
        libcairo2 \
        libasound2 \
        libatspi2.0-0 \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list \
    && curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | gpg --dearmor -o /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends nodejs gh \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from packages stage
COPY --from=packages /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=packages /usr/local/bin /usr/local/bin

# Install Playwright browsers for crawl4ai
RUN playwright install chromium --with-deps

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
