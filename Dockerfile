FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    LOTLINE_DEMO=1 \
    LOTLINE_DATA=/data

WORKDIR /app
COPY requirements.txt ./
RUN apt-get update \
    && apt-get install -y --no-install-recommends fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*
RUN pip install -r requirements.txt
COPY . .

# Optional trained detector. A build without these args still runs (numpy
# baseline, and /readyz says so); a build with them verifies the checksum and
# fails closed on any mismatch. Fetch before seeding so the model card records
# the backend that will actually serve uploads.
ARG LOTLINE_MODEL_URL=""
ARG LOTLINE_MODEL_SHA256=""
RUN if [ -n "$LOTLINE_MODEL_URL" ]; then \
      python scripts/fetch_model.py --url "$LOTLINE_MODEL_URL" --sha256 "$LOTLINE_MODEL_SHA256" --dest data/models; \
    else \
      echo "no model package supplied; demo will use the numpy baseline"; \
    fi

RUN mkdir -p /data /seed \
    && LOTLINE_DATA=/seed python -m app.seed
EXPOSE 8077
CMD ["./start.sh"]
