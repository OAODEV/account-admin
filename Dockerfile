FROM python:3-alpine
MAINTAINER thomas.yager-madden@adops.com

RUN apk update && \
apk add --update musl \
build-base \
postgresql \
postgresql-dev

COPY . /app
WORKDIR /app
RUN echo "0 5 * * * python3 /app/google_directory_sync.py" > /tmp/crontab \
    && crontab /tmp/crontab

RUN pip install -r requirements.txt

EXPOSE 5000

# CMD crond -d 5; python3 admin_app.py
CMD python3 admin_app.py