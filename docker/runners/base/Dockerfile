# ---- Stage 1: tools builder
FROM debian:bookworm-slim AS tools

RUN apt-get update && apt-get install -y --no-install-recommends \
  git curl ca-certificates bash patch ripgrep unzip \
 && rm -rf /var/lib/apt/lists/*

# gh
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
  | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg \
 && chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg \
 && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
  > /etc/apt/sources.list.d/github-cli.list \
 && apt-get update && apt-get install -y gh \
 && rm -rf /var/lib/apt/lists/*

# gitleaks (pinned)
ARG GITLEAKS_VER=8.18.4
RUN curl -L "https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VER}/gitleaks_${GITLEAKS_VER}_linux_x64.tar.gz" \
  -o /tmp/gitleaks.tgz \
 && tar -xzf /tmp/gitleaks.tgz -C /usr/local/bin gitleaks \
 && rm -f /tmp/gitleaks.tgz

# syft + trivy via official scripts
RUN curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s -- -b /usr/local/bin
RUN curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin

# ---- Stage 2: runtime base (smaller)
FROM debian:bookworm-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
  git ca-certificates bash patch ripgrep \
 && rm -rf /var/lib/apt/lists/*

COPY --from=tools /usr/bin/gh /usr/bin/gh
COPY --from=tools /usr/local/bin/gitleaks /usr/local/bin/gitleaks
COPY --from=tools /usr/local/bin/syft /usr/local/bin/syft
COPY --from=tools /usr/local/bin/trivy /usr/local/bin/trivy

ENV PIP_CACHE_DIR=/cache/pip \
    TRIVY_CACHE_DIR=/cache/trivy \
    GH_CONFIG_DIR=/cache/gh \
    XDG_CACHE_HOME=/cache/xdg

WORKDIR /work
