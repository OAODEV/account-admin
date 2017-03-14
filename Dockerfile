FROM python:3-alpine
MAINTAINER thomas.yager-madden@adops.com

RUN apk update && \
apk add --update musl \
build-base \
postgresql \
postgresql-dev

COPY . /app
WORKDIR /app


RUN pip install -r requirements.txt

EXPOSE 5000

CMD python3 admin_app.py
