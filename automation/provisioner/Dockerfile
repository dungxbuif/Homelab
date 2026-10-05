FROM python:3.13-alpine

RUN apk add --no-cache docker-cli

COPY server.py /app/provisioner/server.py

ENTRYPOINT ["python3", "/app/provisioner/server.py"]
