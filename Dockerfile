FROM python:3.11-slim as python-base

# Python settings
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_IN_PROJECT=false \
    POETRY_NO_INTERACTION=1 \
    POETRY_VERSION=2.1.2 \
    PYSETUP_PATH="/opt/pysetup" \
    VENV_PATH="/opt/pysetup/.venv" \
    POETRY_VIRTUALENVS_CREATE=false

# Prepend poetry and venv to path
ENV PATH="$POETRY_HOME/bin:$VENV_PATH/bin:$PATH"

# Builder stage for dependencies
FROM python-base as builder-base

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

# Copy project requirements
WORKDIR $PYSETUP_PATH
COPY poetry.lock pyproject.toml ./

# Install dependencies
RUN pip install --upgrade pip \
    && poetry install --no-root --without dev

# Final stage
FROM python-base as final

# Set working directory
WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy dependencies from builder
COPY --from=builder-base $POETRY_HOME $POETRY_HOME
COPY --from=builder-base /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder-base /usr/local/bin /usr/local/bin

# Copy project files
COPY . /app/

# Create directory for proxies
RUN mkdir -p /app/utils_mount

# Check if Poetry is working
RUN poetry --version

# Run command
CMD ["poetry", "run", "start"]