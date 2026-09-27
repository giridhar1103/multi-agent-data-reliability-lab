FROM python:3.11-slim@sha256:e41613d42d4891e4930f79523f93f81bbc7632584ec65e36ab055f41a800b41e
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 LAB_DATA_DIR=/data LANGSMITH_TRACING=false
WORKDIR /app
COPY requirements.lock pyproject.toml README.md ./
COPY src ./src
RUN --mount=type=secret,id=pip_ca \
    if [ -f /run/secrets/pip_ca ]; then export PIP_CERT=/run/secrets/pip_ca; fi; \
    pip install --no-cache-dir -r requirements.lock && pip install --no-cache-dir --no-deps . \
    && useradd --create-home --uid 10001 lab && mkdir /data && chown lab:lab /data
USER lab
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=15s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"
CMD ["reliability-lab", "serve"]
