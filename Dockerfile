FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    LOTLINE_DEMO=1 \
    LOTLINE_DATA=/data

WORKDIR /app
COPY requirements.txt ./
RUN pip install -r requirements.txt
COPY . .
RUN mkdir -p /data
EXPOSE 8077
CMD ["./start.sh"]
