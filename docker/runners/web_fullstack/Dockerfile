FROM python:3.12-slim AS pytools
RUN pip install --no-cache-dir pytest

FROM agent-factory/runner-base:0.1.0
COPY --from=pytools /usr/local /usr/local

# Optional: preinstall common libs for faster runs
# RUN pip install -U pip ruff black jsonschema

WORKDIR /work
