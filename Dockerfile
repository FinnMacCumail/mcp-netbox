# Stage 1: Build stage with development tools
# Use latest Python 3.12 for better security patches
FROM python:3.12-slim-bookworm AS builder

# Update packages and install build dependencies with security updates
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Set the working directory. All subsequent commands will be executed here.
WORKDIR /app

# Copy dependency definitions first.
# By doing this separately, Docker can cache this layer if dependencies don't change.
COPY pyproject.toml README.md ./

# Upgrade pip and install latest secure versions of build tools
RUN pip install --no-cache-dir --upgrade \
    pip>=24.0 \
    setuptools>=75.0.0 \
    wheel>=0.44.0

# Install project dependencies.
# This installs packages in the system site-packages, which is cleaner for the next stage.
RUN pip install --no-cache-dir .

# Copy the rest of the application code.
COPY . .

# Stage 2: Production runtime image
FROM python:3.12-slim-bookworm AS runtime

# Create a non-root user for extra security.
RUN useradd --create-home --shell /bin/bash --uid 1000 netbox

# Set the working directory in the new user's home directory.
WORKDIR /home/netbox/app

# Copy installed packages and required application code from the builder stage.
# This is the essence of a multi-stage build: only the result is carried forward.
COPY --from=builder --chown=netbox:netbox /app /home/netbox/app
COPY --from=builder --chown=netbox:netbox /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder --chown=netbox:netbox /usr/local/bin /usr/local/bin

# Install only essential runtime dependencies with security updates
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Switch to the non-root user.
USER netbox

# Expose the port on which the application runs.
EXPOSE 8080

# Configure the health check for Docker container orchestration
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8080/readyz || exit 1

# Set environment variables.
ENV PATH="/home/netbox/.local/bin:${PATH}"
ENV PYTHONUNBUFFERED=1

# The command to start the server.
CMD ["python", "main.py"]