FROM alpine
MAINTAINER thomas.yager-madden@adops.com

RUN apk add --no-cache python3 py3-psycopg2 git \
&& ln -s /usr/bin/python3 /bin/python
COPY . /app
WORKDIR /app
RUN echo "0 5 * * * python3 /app/google_directory_sync.py" > /etc/crontabs/root

RUN pip3 install pipenv --upgrade \
&& pipenv install --skip-lock --system

EXPOSE 5000

CMD gunicorn -b 0.0.0.0:5000 admin_app:app --log-file=-
