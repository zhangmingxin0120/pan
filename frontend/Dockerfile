ARG NODE_IMAGE=m.daocloud.io/docker.io/library/node:22.17.0-alpine3.21
ARG NGINX_IMAGE=m.daocloud.io/docker.io/library/nginx:1.28.0-alpine3.21
FROM ${NODE_IMAGE} AS builder

WORKDIR /app
RUN npm config set registry https://registry.npmmirror.com
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM ${NGINX_IMAGE}
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
HEALTHCHECK --interval=10s --timeout=3s --retries=5 CMD wget -q -O /dev/null http://127.0.0.1/health || exit 1

