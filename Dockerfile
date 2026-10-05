# Provar — assurance layer for hospital AI
FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY provar ./provar

RUN pip install --no-cache-dir .

# Default: offline one-command demo (no network, no keys needed)
ENTRYPOINT ["provar"]
CMD ["demo"]
