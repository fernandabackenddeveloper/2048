FROM agent-factory/runner-base:0.1.0

ARG GODOT_VER=4.3
RUN apt-get update && apt-get install -y --no-install-recommends wget unzip \
 && rm -rf /var/lib/apt/lists/*

RUN wget -O /tmp/godot.zip "https://github.com/godotengine/godot/releases/download/${GODOT_VER}-stable/Godot_v${GODOT_VER}-stable_linux.x86_64.zip" \
 && unzip /tmp/godot.zip -d /usr/local/bin \
 && rm -f /tmp/godot.zip \
 && ln -sf /usr/local/bin/Godot_* /usr/local/bin/godot

WORKDIR /work
