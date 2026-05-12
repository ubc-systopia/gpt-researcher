# Stage 1: Browser and build tools installation
# Python 3.12+ required for LangChain v1
FROM python:3.12-slim-bookworm AS install-browser

# Install Chromium, Chromedriver, Firefox, Geckodriver, and build tools in one layer
RUN apt-get update \
    && apt-get install -y gnupg wget ca-certificates --no-install-recommends \
    && ARCH=$(dpkg --print-architecture) \
    && wget -qO - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=${ARCH}] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y chromium chromium-driver \
    && chromium --version && chromedriver --version \
    && apt-get install -y --no-install-recommends firefox-esr build-essential \
    && GECKO_ARCH=$(case ${ARCH} in amd64) echo "linux64" ;; arm64) echo "linux-aarch64" ;; *) echo "linux64" ;; esac) \
    && wget https://github.com/mozilla/geckodriver/releases/download/v0.36.0/geckodriver-v0.36.0-${GECKO_ARCH}.tar.gz \
    && tar -xvzf geckodriver-v0.36.0-${GECKO_ARCH}.tar.gz \
    && chmod +x geckodriver \
    && mv geckodriver /usr/local/bin/ \
    && rm geckodriver-v0.36.0-${GECKO_ARCH}.tar.gz \
    && rm -rf /var/lib/apt/lists/*  # Clean up apt lists to reduce image size

# Stage 2: Python dependencies installation
FROM install-browser AS gpt-researcher-install

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PIP_ROOT_USER_ACTION=ignore
WORKDIR /app

# Copy and install Python dependencies in a single layer to optimize cache usage
COPY ./requirements.txt ./requirements.txt
COPY ./multi_agents/requirements.txt ./multi_agents/requirements.txt

RUN uv pip install --system --no-cache -r requirements.txt -r multi_agents/requirements.txt

# Stage 3: Final stage with non-root user and app
FROM gpt-researcher-install AS gpt-researcher

# Basic server configuration
ARG HOST=0.0.0.0
ENV HOST=${HOST}
ARG PORT=8000
ENV PORT=${PORT}
EXPOSE ${PORT}

# Uvicorn parameters used in CMD
ARG WORKERS=1
ENV WORKERS=${WORKERS}

# Create a non-root user for security
RUN useradd -ms /bin/bash gpt-researcher && \
    chown -R gpt-researcher:gpt-researcher /app && \
    mkdir -p /app/outputs /app/logs && \
    chown -R gpt-researcher:gpt-researcher /app/outputs /app/logs && \
    chmod 777 /app/outputs /app/logs

USER gpt-researcher
WORKDIR /app

# Copy the rest of the application files with proper ownership
COPY --chown=gpt-researcher:gpt-researcher ./ ./

CMD ["python", "cli.py"]
