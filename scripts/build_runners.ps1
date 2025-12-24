docker build -t agent-factory/runner-base:0.1.0 -f docker/runners/base/Dockerfile docker/runners/base
docker build -t agent-factory/runner-web_fullstack:0.1.0 -f docker/runners/web_fullstack/Dockerfile docker/runners/web_fullstack
docker build -t agent-factory/runner-godot_desktop:0.1.0 -f docker/runners/godot_desktop/Dockerfile docker/runners/godot_desktop
