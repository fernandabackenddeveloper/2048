FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl ca-certificates bash patch ripgrep unzip \
 && rm -rf /var/lib/apt/lists/*

# --- gh (GitHub CLI)
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
    | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg \
 && chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg \
 && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
    > /etc/apt/sources.list.d/github-cli.list \
 && apt-get update && apt-get install -y gh \
 && rm -rf /var/lib/apt/lists/*

# --- gitleaks
RUN curl -L https://github.com/gitleaks/gitleaks/releases/latest/download/gitleaks_8.18.4_linux_x64.tar.gz \
    -o /tmp/gitleaks.tgz \
 && tar -xzf /tmp/gitleaks.tgz -C /usr/local/bin gitleaks \
 && rm -f /tmp/gitleaks.tgz

# --- syft
RUN curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh \
  | sh -s -- -b /usr/local/bin

# --- trivy
RUN curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh \
  | sh -s -- -b /usr/local/bin

WORKDIR /work
