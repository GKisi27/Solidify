# Stage 1 — build the react app
FROM node:20 AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build
# output is in /app/dist

# Stage 2 — serve with nginx
FROM nginx:alpine

# copy built files into nginx
COPY --from=build /app/dist /usr/share/nginx/html

# copy nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]