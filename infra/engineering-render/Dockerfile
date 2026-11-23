FROM node:22-bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg ca-certificates libnss3 libatk-bridge2.0-0 libx11-xcb1 libxcomposite1 libxdamage1 libxrandr2 libgbm1 libasound2 libatk1.0-0 libcups2 libdrm2 libxkbcommon0 libpango-1.0-0 libcairo2 libglib2.0-0 && rm -rf /var/lib/apt/lists/* && useradd -u 10001 -m renderer
WORKDIR /opt/engine
COPY packages/engineering-template/package*.json ./
RUN npm ci --no-audit --no-fund
RUN npm install --no-save @remotion/cli@4.0.538 && npx remotion browser ensure
COPY packages/engineering-template/render.mjs packages/engineering-template/review-plan.mjs packages/engineering-template/render-capabilities.mjs ./
COPY infra/engineering-render/run.mjs ./run.mjs
RUN mkdir /output && chown renderer:renderer /output
USER renderer
ENTRYPOINT ["node","/opt/engine/run.mjs"]
