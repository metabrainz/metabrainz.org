ARG PYTHON_BASE_IMAGE_VERSION=3.8-20210115
ARG NODE_VERSION=16-alpine
FROM metabrainz/python:$PYTHON_BASE_IMAGE_VERSION as metabrainz-dev

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

WORKDIR /code

COPY requirements.txt /code/
RUN pip3 install pip==21.0.1
RUN pip install --no-cache-dir -r requirements.txt

COPY . /code/

#####################################################################################################
# NOTE: The javascript files are continously watched and compiled using this image in developement. #
#####################################################################################################
FROM node:$NODE_VERSION as metabrainz-frontend-dev

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
FROM metabrainz-frontend-dev as metabrainz-frontend-prod

# Compile front-end (static) files
COPY ./frontend /code/frontend
RUN npm run build:prod


###########################################
# NOTE: The production image starts here. #
###########################################
FROM metabrainz-base as metabrainz-prod

COPY ./docker/prod/consul-template-uwsgi.conf /etc/

COPY ./docker/prod/uwsgi.service /etc/service/uwsgi/run
RUN chmod 755 /etc/service/uwsgi/run
COPY ./docker/prod/uwsgi.ini /etc/uwsgi/uwsgi.ini

# copy the compiled js files and static assets from image to prod
COPY --from=metabrainz-frontend-prod /code/frontend/robots.txt /static/
COPY --from=metabrainz-frontend-prod /code/frontend/fonts /static/fonts
COPY --from=metabrainz-frontend-prod /code/frontend/img /static/img
COPY --from=metabrainz-frontend-prod /code/frontend/js/lib /static/js/lib
COPY --from=metabrainz-frontend-prod /code/frontend/dist /static/dist

# Now install our code, which may change frequently
COPY docker /code/metabrainz/

WORKDIR /code/metabrainz
# Ensure we use the right files and folders by removing duplicates
RUN rm -rf ./frontend/
RUN rm -f /code/metabrainz/metabrainz/config.py /code/metabrainz/metabrainz/config.pyc

ARG GIT_COMMIT_SHA
LABEL org.label-schema.vcs-ref=$GIT_COMMIT_SHA
ENV GIT_SHA ${GIT_COMMIT_SHA}
