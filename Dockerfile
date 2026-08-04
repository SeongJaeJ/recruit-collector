FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Seoul

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir playwright \
    && playwright install --with-deps chromium \
    && rm -rf /var/lib/apt/lists/*

COPY job_reporter.py ./

ENTRYPOINT ["python", "job_reporter.py"]
CMD ["--schedule"]
