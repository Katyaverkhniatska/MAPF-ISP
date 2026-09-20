ARG PYTHON_VERSION=3.11.8
FROM python:${PYTHON_VERSION}-slim AS base

# Prevents Python from writing pyc files and buffers.
ENV PYTHONTDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install Tkinter system libraries, Xvfb, and xauth for virtual display support
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-tk \
    tk-dev \
    xvfb \
    xauth \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create a non-privileged user.
ARG UID=10001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/nonexistent" \
    --shell "/sbin/nologin" \
    --no-create-home \
    --uid "${UID}" \
    appuser

# Install Python dependencies.
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=bind,source=requirements.txt,target=requirements.txt \
    python -m pip install -r requirements.txt

# Copy source code.
COPY . .

USER appuser

CMD ["python", "main.py"]