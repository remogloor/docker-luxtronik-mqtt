FROM python:alpine as base
FROM base as builder


# Install pip requirements
RUN mkdir /install
WORKDIR /install
COPY requirements.txt /requirements.txt
RUN pip install --prefix=/install -r /requirements.txt

FROM base

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

COPY --from=builder /install /usr/local

WORKDIR /app
ADD app /app

# Switching to a non-root user, please refer to https://aka.ms/vscode-docker-python-user-rights
RUN addgroup -S appgroup && adduser -S appuser -G appgroup && chown -R appuser:appgroup /app
USER appuser

HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
    CMD ["/bin/sh", "-c", "/app/healthcheck.sh"]

# During debugging, this entry point will be overridden. For more information, please refer to https://aka.ms/vscode-docker-python-debug
CMD ["python", "main.py"]
