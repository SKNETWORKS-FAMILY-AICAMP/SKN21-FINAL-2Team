FROM node:20-slim

WORKDIR /app

COPY package*.json ./

RUN npm install

COPY . .

# Expose port 3000
EXPOSE 3000

# Run in development mode
CMD ["npm", "run", "dev"]
