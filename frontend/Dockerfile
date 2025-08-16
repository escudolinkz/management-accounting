# syntax=docker/dockerfile:1
FROM node:20-alpine AS base
RUN apk add --no-cache tini
WORKDIR /app
COPY package*.json ./
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi
COPY . .
RUN npm run build
USER 1000:1000
USER 1000:1000
EXPOSE 8080
ENV PORT=8080
ENTRYPOINT ["/sbin/tini", "--"]
CMD ["npm", "run", "start"]
