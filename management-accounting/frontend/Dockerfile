# syntax=docker/dockerfile:1
FROM node:20-alpine AS base
RUN apk add --no-cache tini
RUN adduser -D -u 1000 appuser
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci
COPY frontend ./
RUN npm run build
USER 1000:1000
EXPOSE 8080
ENV PORT=8080
ENTRYPOINT ["/sbin/tini", "--"]
CMD ["npm", "run", "start"]
