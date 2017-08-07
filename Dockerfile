FROM python:3-alpine3.6
MAINTAINER thomas.yager-madden@adops.com

RUN apk add --update py3-psycopg2


COPY . /app
WORKDIR /app
RUN echo "0 5 * * * python3 /app/google_directory_sync.py" > /tmp/crontab \
    && crontab /tmp/crontab

RUN pip install -r requirements.txt

EXPOSE 5000

CMD gunicorn -b 0.0.0.0:5000 admin_app:app --log-file=-
