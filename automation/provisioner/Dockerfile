FROM docker:27.5.1-cli@sha256:851f91d241214e7c6db86513b270d58776379aacc5eb9c4a87e5b47115e3065c AS dockercli
FROM python:3.13-alpine@sha256:2d9aefe2fef018a7eb2c13064c89c71929800fd2e5dccdbf52ea5da5bb8d929a

COPY --from=dockercli /usr/local/bin/docker /usr/local/bin/docker
COPY automation/provisioner/server.py /app/provisioner/server.py
COPY backup/scripts/common.py backup/scripts/provisioner.py backup/scripts/register_resource.py backup/scripts/validate_provision_request.py /app/provisioner/scripts/

ENV SCRIPTS_PATH=/app/provisioner/scripts

ENTRYPOINT ["python3", "/app/provisioner/server.py"]
