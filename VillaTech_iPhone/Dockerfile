FROM node:24-bookworm-slim
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY --chown=node:node App.js Drafts.js app.json navigation.cjs ./
COPY --chown=node:node assets ./assets
RUN chown node:node /app
ENV CI=1 EXPO_NO_TELEMETRY=1
USER node
CMD ["sh", "-c", "exec ./node_modules/.bin/expo start --go --host lan --port \"${PORT:-8081}\""]
