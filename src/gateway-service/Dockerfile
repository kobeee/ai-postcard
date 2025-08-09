FROM node:18-alpine AS base
WORKDIR /app
COPY package*.json ./
# 生产依赖安装（后续根据锁文件完善）
RUN npm ci --only=production || npm ci
COPY . .
EXPOSE 8080
CMD ["node", "index.js"]
