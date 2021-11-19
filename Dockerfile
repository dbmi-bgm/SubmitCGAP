FROM python:3.7-slim-buster

ARG APP_USER
ENV APP_USER=${APP_USER:-"submitter"}
ENV PYTHONFAULTHANDLER=1 \
  PYTHONUNBUFFERED=1 \
  PYTHONHASHSEED=random \
  PIP_NO_CACHE_DIR=off \
  PIP_DISABLE_PIP_VERSION_CHECK=on \
  PIP_DEFAULT_TIMEOUT=100 \
  POETRY_VERSION=1.1.11

# Create a user for running the package
RUN useradd -ms /bin/bash $APP_USER

# Update OS level packages
RUN apt-get update && apt-get install -y make bash

# Configure venv
ENV VIRTUAL_ENV=/opt/venv
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN chown -R $APP_USER:$APP_USER /opt/venv && \
    mkdir -p /home/$APP_USER/SubmitCGAP

WORKDIR /home/$APP_USER/SubmitCGAP

# Upgrade pip, install in layer
RUN pip install --upgrade pip && \
    pip install poetry==$POETRY_VERSION

# Install dependencies
COPY pyproject.toml .
COPY poetry.lock .
RUN poetry install --no-root

# Copy package
COPY . .
RUN poetry install

# Give user perms
RUN chown -R $APP_USER:$APP_USER /home/$APP_USER/SubmitCGAP

USER $APP_USER

ENTRYPOINT ["/bin/bash"]