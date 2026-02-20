FROM node:20-slim
WORKDIR /app
COPY package*.json ./
# --no-package-lock을 써서 서버 아키텍처에 맞는 패키지를 새로 받게 합니다.
# RUN sudo apt install npm -y
RUN npm install --no-package-lock
COPY . .
EXPOSE 3000
CMD ["npm", "run", "dev"]