FROM mcr.microsoft.com/playwright:v1.56.1-noble
WORKDIR /runner
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-venv && rm -rf /var/lib/apt/lists/*
RUN npm init -y && npm install --save-exact playwright@1.56.1 && rm -rf /root/.npm
COPY capture.mjs /runner/capture.mjs
COPY project-runner.mjs /runner/project-runner.mjs
RUN python3 -m venv /opt/python && /opt/python/bin/pip install fastapi==0.115.12 uvicorn==0.34.2
RUN mkdir -p /opt/node-seed && cd /opt/node-seed && npm init -y && \
    npm install --cache /opt/npm-cache vite@6.3.5 react@19.2.0 react-dom@19.2.0 vue@3.5.13 typescript@5.9.3 && \
    rm -rf /opt/node-seed/node_modules
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
ENTRYPOINT []

