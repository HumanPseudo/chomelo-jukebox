FROM node:22-alpine
WORKDIR /code
ARG VITE_ENTRY
ARG VITE_API_URL=/api/v1
ENV VITE_ENTRY=$VITE_ENTRY
ENV VITE_API_URL=$VITE_API_URL
COPY package.json package-lock.json ./
RUN npm install
COPY . .
RUN npm run build
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
