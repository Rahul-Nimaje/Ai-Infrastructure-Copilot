FROM node:22-alpine AS base
WORKDIR /srv

COPY package.json package-lock.json* /srv/
COPY apps/web/package.json /srv/apps/web/package.json
COPY packages/shared-types /srv/packages/shared-types

RUN npm install --no-audit --no-fund

COPY apps/web /srv/apps/web

WORKDIR /srv/apps/web
RUN npm run build

EXPOSE 3000
CMD ["npm", "run", "start"]
