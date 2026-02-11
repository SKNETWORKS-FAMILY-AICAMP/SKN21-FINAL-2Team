FROM node:20-slim

WORKDIR /app

COPY package*.json ./

RUN rm -f package-lock.json && npm install && \
    cp node_modules/lightningcss-linux-arm64-gnu/lightningcss.linux-arm64-gnu.node node_modules/lightningcss/ || true

COPY . .

# Expose port 3000
EXPOSE 3000

# Run in development mode
CMD ["npm", "run", "dev"]
