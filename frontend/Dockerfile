FROM node:24-alpine AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci

# dev 段：Vite dev サーバ（Step 5 の override で使用）
FROM deps AS dev
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host"]

# build 段：静的ファイル生成（イメージビルド時に npm run build）
FROM deps AS build
COPY . .
RUN npm run build

# prod 段：nginx が静的配信＋/api 逆プロキシ
FROM nginx:alpine AS prod
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80