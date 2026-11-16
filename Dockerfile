FROM node:22-bookworm-slim AS web
WORKDIR /app
COPY package.json package-lock.json ./
COPY apps/studio/package.json apps/studio/package.json
COPY packages/video/package.json packages/video/package.json
RUN npm ci --no-audit --no-fund
COPY apps/studio apps/studio
COPY packages/video packages/video
COPY assets assets
RUN npm run build

FROM python:3.12-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg espeak-ng curl ca-certificates \
    libnss3 libatk-bridge2.0-0 libx11-xcb1 libxcomposite1 libxdamage1 libxrandr2 libgbm1 libasound2 \
    libatk1.0-0 libcups2 libdrm2 libxkbcommon0 libpango-1.0-0 libcairo2 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=web /usr/local/bin/node /usr/local/bin/node
WORKDIR /app
COPY apps/api apps/api
RUN pip install --no-cache-dir ./apps/api
COPY --from=web /app/node_modules node_modules
COPY --from=web /app/apps/studio/dist apps/studio/dist
COPY --from=web /app/packages/video packages/video
COPY assets assets
COPY scripts scripts
COPY docs docs
COPY packages/engineering-template packages/engineering-template
COPY package.json ./
ENV PYTHONPATH=/app/apps/api/src EXPLAINER_DATA_DIR=/data
RUN node node_modules/@remotion/cli/remotion-cli.js browser ensure && \
    useradd -m -u 10001 studio && mkdir -p /data /app/node_modules/.cache /app/node_modules/.remotion && \
    chown -R studio:studio /data /app/node_modules/.cache /app/node_modules/.remotion
USER studio
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD ["python","-c","import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health',timeout=3)"]
CMD ["python","scripts/serve.py"]

