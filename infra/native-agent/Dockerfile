FROM node:22-bookworm-slim
ARG PROVIDER=codex
ARG CODEX_VERSION=0.165.0
ARG CLAUDE_VERSION=2.1.312
RUN apt-get update && apt-get install -y --no-install-recommends python3 git ripgrep ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -u 10001 agent
RUN if [ "$PROVIDER" = codex ]; then npm install -g @openai/codex@"$CODEX_VERSION"; \
    elif [ "$PROVIDER" = claude-code ]; then npm install -g @anthropic-ai/claude-code@"$CLAUDE_VERSION"; \
    else exit 1; fi
COPY services/native_agent/driver.py /agent/driver.py
ENV HOME=/home/agent CODEX_HOME=/home/agent/.codex \
    DISABLE_AUTOUPDATER=1 DISABLE_TELEMETRY=1 DISABLE_ERROR_REPORTING=1
WORKDIR /workspace
USER agent
ENTRYPOINT ["python3", "/agent/driver.py"]
