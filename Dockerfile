FROM metabrainz/python:3.6-1

##############
# MetaBrainz #
##############

RUN mkdir /code
WORKDIR /code

# Node and dependencies
RUN curl -sL https://deb.nodesource.com/setup_7.x | bash -
RUN apt-get install -y nodejs
COPY ./package.json /code/
RUN npm install

# Python dependencies
RUN apt-get update \
     && apt-get install -y --no-install-recommends \
                        build-essential \
                        git \
                        libpq-dev \
                        libtiff5-dev \
                        libffi-dev \
                        libxml2-dev \
                        libxslt1-dev \
                        libssl-dev \
     && rm -rf /var/lib/apt/lists/*
COPY requirements.txt /code/
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir uWSGI==2.0.15

COPY . /code/
RUN ./node_modules/.bin/lessc ./metabrainz/static/css/main.less > ./metabrainz/static/css/main.css
RUN ./node_modules/.bin/lessc ./metabrainz/static/css/theme/boostrap/boostrap.less > ./metabrainz/static/css/theme/boostrap/boostrap.css
RUN ./node_modules/.bin/lessc ./metabrainz/static/fonts/font_awesome/less/font-awesome.less > ./metabrainz/static/fonts/font_awesome/less/font-awesome.css

############
# Services #
############

# Consul Template service is already set up with the base image.
# Just need to copy the configuration.
COPY ./docker/prod/consul-template-uwsgi.conf /etc/

COPY ./docker/prod/uwsgi.service /etc/service/uwsgi/run
RUN chmod 755 /etc/service/uwsgi/run
COPY ./docker/prod/uwsgi.ini /etc/uwsgi/uwsgi.ini

EXPOSE 13031
