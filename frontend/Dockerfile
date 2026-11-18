FROM node:22-alpine
WORKDIR /code
ARG VITE_ENTRY
ENV VITE_ENTRY=$VITE_ENTRY
COPY package.json package-lock.json ./
RUN npm install
COPY . .
RUN npm run build
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
