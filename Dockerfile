# Stage 1: build dependencies
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build tools
RUN pip install --no-cache-dir hatchling

# Copy only files needed for dependency resolution
COPY pyproject.toml .
COPY src/ src/

# Install package and dependencies into /install prefix
RUN pip install --no-cache-dir --prefix=/install .


# Stage 2: final image
FROM python:3.12-slim

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash vault

# Copy installed dependencies from builder
COPY --from=builder /install /usr/local

# Copy source code
COPY src/ /app/src/

# Set working directory and Python path
WORKDIR /app
ENV PYTHONPATH=/app/src

# Vault directory — users mount their local vault here with -v
VOLUME ["/vault"]
ENV VAULT_LOCAL_PATH=/vault

# Disable .env file loading in container (env vars passed via docker run)
ENV VAULT_DISABLE_DOTENV=1

USER vault

ENTRYPOINT ["python", "-m", "vault_mcp"]
