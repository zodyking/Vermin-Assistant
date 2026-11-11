FROM node:22-alpine AS ui
WORKDIR /ui
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-alpine
RUN apk add --no-cache tzdata
WORKDIR /opt/vermin_assistant
COPY app/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY --from=ui /ui/dist ./static
RUN python -m app.audio
ENV PYTHONUNBUFFERED=1
EXPOSE 8099
CMD ["python", "-m", "app.server"]
