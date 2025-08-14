# Stage 1: Build the Vue application
FROM node:20-alpine as build-stage
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
# Add executable permissions to the vite command
RUN chmod +x /app/node_modules/.bin/vite
RUN npm run build

# Stage 2: Serve the built assets with Nginx
FROM nginx:stable-alpine as production-stage
COPY --from=build-stage /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]