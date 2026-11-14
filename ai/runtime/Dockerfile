FROM python:3.12-slim-bookworm@sha256:34386ef0cb081344d7ec1c103ba398e6e9f64e9ab3a1509accc92a4e24a07258
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 libzstd1 \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt /tmp/requirements.txt
RUN python -m pip install --no-cache-dir -r /tmp/requirements.txt && python -m pip check
RUN useradd --create-home --uid 1000 worker
USER worker
WORKDIR /workspace
CMD ["python", "--version"]
