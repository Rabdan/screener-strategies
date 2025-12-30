FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

FROM node:20-alpine

WORKDIR /app
COPY --from=builder /app/package*.json ./
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/build ./build

EXPOSE 5173
# For SvelteKit dev mode or preview. If user wants production, he would use 'node build'.
# But typically for dev it's 'npm run dev -- --host'
CMD ["npm", "run", "dev", "--", "--host"]
