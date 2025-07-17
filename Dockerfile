ARG PYTHON_BASE_IMAGE_VERSION=3.11-20231006
ARG NODE_VERSION=18-alpine
FROM metabrainz/python:$PYTHON_BASE_IMAGE_VERSION AS metabrainz-base

ARG PYTHON_BASE_IMAGE_VERSION

LABEL org.label-schema.vcs-url="https://github.com/metabrainz/metabrainz.org.git" \
      org.label-schema.vcs-ref="" \
      org.label-schema.schema-version="1.0.0-rc1" \
      org.label-schema.vendor="MetaBrainz Foundation" \
      org.label-schema.name="MetaBrainz" \
      org.metabrainz.based-on-image="metabrainz/python:$PYTHON_BASE_IMAGE_VERSION"

ENV DOCKERIZE_VERSION v0.6.1
RUN wget https://github.com/jwilder/dockerize/releases/download/$DOCKERIZE_VERSION/dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz \
    && tar -C /usr/local/bin -xzvf dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz

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
                        wget \
     && rm -rf /var/lib/apt/lists/*

# While WORKDIR will create a directory if it doesn't already exist, we do it explicitly here
# so that we know what user it is created as: https://github.com/moby/moby/issues/36677
RUN mkdir -p /code/metabrainz /static

WORKDIR /code/metabrainz

COPY requirements.txt /code/metabrainz
RUN pip3 install pip==21.0.1
RUN pip install --no-cache-dir -r requirements.txt

############################################
# NOTE: The development image starts here. #
############################################
FROM metabrainz-base AS metabrainz-dev
COPY . /code/metabrainz

#####################################################################################################
# NOTE: The javascript files are continously watched and compiled using this image in developement. #
#####################################################################################################
FROM node:$NODE_VERSION AS metabrainz-frontend-dev

ARG NODE_VERSION

LABEL org.label-schema.vcs-url="https://github.com/metabrainz/metabrainz.org.git" \
      org.label-schema.vcs-ref="" \
      org.label-schema.schema-version="1.0.0-rc1" \
      org.label-schema.vendor="MetaBrainz Foundation" \
      org.label-schema.name="MetaBrainz Static Builder" \
      org.metabrainz.based-on-image="node:$NODE_VERSION"

RUN mkdir /code
WORKDIR /code

COPY package.json package-lock.json /code/
RUN npm install

COPY webpack.config.js babel.config.js tsconfig.json .eslintrc.js .stylelintrc.js /code/


#########################################################################
# NOTE: The javascript files for production are compiled in this image. #
#########################################################################
FROM metabrainz-frontend-dev AS metabrainz-frontend-prod

# Compile front-end (static) files
COPY ./frontend /code/frontend
RUN npm run build:prod


###########################################
# NOTE: The production image starts here. #
###########################################
FROM metabrainz-base AS metabrainz-prod

RUN pip install --no-cache-dir uWSGI==2.0.23

COPY ./docker/web/consul-template-web.conf /etc/
COPY ./docker/web/web.service /etc/service/web/run
COPY ./docker/web/web.ini /etc/uwsgi/web.ini
RUN chmod 755 /etc/service/web/run
RUN touch /etc/service/web/down

COPY ./docker/oauth/consul-template-oauth.conf /etc/
COPY ./docker/oauth/oauth.service /etc/service/oauth/run
COPY ./docker/oauth/oauth.ini /etc/uwsgi/oauth.ini
RUN chmod 755 /etc/service/oauth/run
RUN touch /etc/service/oauth/down

COPY ./docker/rc.local /etc/rc.local

# Create directory for cron logs.
RUN mkdir /logs

# crontab
COPY ./docker/services/cron/crontab /etc/cron.d/crontab
RUN chmod 0644 /etc/cron.d/crontab

# copy the compiled js files and static assets from image to prod
COPY --from=metabrainz-frontend-prod /code/frontend/robots.txt /static/
COPY --from=metabrainz-frontend-prod /code/frontend/fonts /static/fonts
COPY --from=metabrainz-frontend-prod /code/frontend/img /static/img
COPY --from=metabrainz-frontend-prod /code/frontend/js/lib /static/js/lib
COPY --from=metabrainz-frontend-prod /code/frontend/dist /static/dist

# Now install our code, which may change frequently
COPY . /code/metabrainz/

# Ensure we use the right files and folders by removing duplicates
RUN rm -rf ./frontend/
RUN rm -f /code/metabrainz/metabrainz/config.py /code/metabrainz/metabrainz/config.pyc

ARG GIT_COMMIT_SHA
LABEL org.label-schema.vcs-ref=$GIT_COMMIT_SHA
ENV GIT_SHA ${GIT_COMMIT_SHA}
