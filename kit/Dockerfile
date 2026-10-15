# syntax=docker/dockerfile:1
# llm-code-gates tool image: every gate tool pinned (binaries by sha256, Python by --require-hashes), nothing
# installed on the host. Build:   docker build -t llm-code-gates-tools:0.1 -f gates/Dockerfile gates
# Run in a repo:                docker run --rm --cpus 2 --memory 3g -v "$PWD":/work -w /work \
#                                 llm-code-gates-tools:0.1 task check BASE_REF=origin/main
# Status in the research: written and statically linted (hadolint) only; NOT built or run (live-Docker use was
# not approved). No Trivy: excluded after GHSA-69fq-xp46-6x23 (CVE-2026-33634).
FROM python:3.12-slim-bookworm@sha256:34386ef0cb081344d7ec1c103ba398e6e9f64e9ab3a1509accc92a4e24a07258 AS fetch
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
# hadolint ignore=DL3008
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl xz-utils \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /dl
COPY docker/binaries.txt /dl/binaries.txt
RUN set -eu; grep -v '^#' binaries.txt | while IFS='|' read -r name url sum; do \
      curl -fsSL --retry 3 -o "$name" "$url"; echo "$sum  $name" | sha256sum -c -; \
    done
RUN mkdir -p /out && tar -xzf task.tgz -C /out task && tar -xzf gitleaks.tgz -C /out gitleaks \
    && tar -xzf actionlint.tgz -C /out actionlint && tar -xzf syft.tgz -C /out syft && tar -xzf grype.tgz -C /out grype \
    && tar -xJf shellcheck.txz && cp shellcheck-v0.11.0/shellcheck /out/ \
    && install -m 0755 osv-scanner /out/osv-scanner && install -m 0755 hadolint /out/hadolint && chmod 0755 /out/*

FROM python:3.12-slim-bookworm@sha256:34386ef0cb081344d7ec1c103ba398e6e9f64e9ab3a1509accc92a4e24a07258
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
# hadolint ignore=DL3008
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*
COPY --from=fetch /out/ /usr/local/bin/
COPY docker/requirements-tools.txt docker/requirements-semgrep.txt /tmp/req/
# Two venvs: semgrep pins its own jsonschema; every wheel is hash-checked
RUN python -m venv /opt/tools && /opt/tools/bin/pip install --no-cache-dir --require-hashes -r /tmp/req/requirements-tools.txt \
    && python -m venv /opt/semgrep && /opt/semgrep/bin/pip install --no-cache-dir --require-hashes -r /tmp/req/requirements-semgrep.txt \
    && ln -s /opt/semgrep/bin/semgrep /usr/local/bin/semgrep && rm -rf /tmp/req
ENV PATH="/opt/tools/bin:${PATH}" \
    SEMGREP_SEND_METRICS=off \
    PYTHONDONTWRITEBYTECODE=1
RUN useradd --create-home --uid 10001 gates && git config --system --add safe.directory /work
USER 10001
WORKDIR /work
CMD ["task", "--list"]
