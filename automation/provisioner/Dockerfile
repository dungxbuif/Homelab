FROM docker:29.9.0-cli@sha256:1a4c7cb63513f349bdad01fcc6e0f3f2f67d37b9da86f14dc0d4a0942eecda00 AS dockercli
FROM python:3.13-alpine@sha256:2d9aefe2fef018a7eb2c13064c89c71929800fd2e5dccdbf52ea5da5bb8d929a AS target-python

FROM --platform=$BUILDPLATFORM python:3.13-alpine@sha256:2d9aefe2fef018a7eb2c13064c89c71929800fd2e5dccdbf52ea5da5bb8d929a AS prepare
COPY --from=target-python / /target/
COPY automation/provisioner/remove_build_pip.py /remove_build_pip.py
RUN python /remove_build_pip.py /target

FROM scratch
COPY --from=prepare /target/ /
ENV PATH=/usr/local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin

COPY --from=dockercli /usr/local/bin/docker /usr/local/bin/docker
COPY automation/provisioner/server.py /app/provisioner/server.py
COPY backup/scripts/common.py backup/scripts/provisioner.py backup/scripts/register_resource.py backup/scripts/validate_provision_request.py /app/provisioner/scripts/

ENV SCRIPTS_PATH=/app/provisioner/scripts

ENTRYPOINT ["python3", "/app/provisioner/server.py"]
