ARG PYTHON_BASE_IMAGE_VERSION=3.13-20260216
ARG NODE_VERSION=26-alpine
FROM metabrainz/python:$PYTHON_BASE_IMAGE_VERSION AS metabrainz-python-base

ARG PYTHON_BASE_IMAGE_VERSION

LABEL org.label-schema.vcs-url="https://github.com/metabrainz/metabrainz.org.git" \
      org.label-schema.vcs-ref="" \
      org.label-schema.schema-version="1.0.0-rc1" \
      org.label-schema.vendor="MetaBrainz Foundation" \
      org.label-schema.name="MetaBrainz" \
      org.metabrainz.based-on-image="metabrainz/python:$PYTHON_BASE_IMAGE_VERSION"

ENV DOCKERIZE_VERSION=v0.6.1
RUN wget https://github.com/jwilder/dockerize/releases/download/$DOCKERIZE_VERSION/dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz \
    && tar -C /usr/local/bin -xzvf dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz

# While WORKDIR will create a directory if it doesn't already exist, we do it explicitly here
# so that we know what user it is created as: https://github.com/moby/moby/issues/36677
RUN mkdir -p /code/metabrainz /static

WORKDIR /code/metabrainz

RUN pip3 install --no-cache-dir pip==26.1.2

FROM metabrainz-python-base AS metabrainz-python-deps

RUN apt-get update \
     && apt-get install -y --no-install-recommends \
                        git \
     && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /code/metabrainz
RUN pip wheel --no-cache-dir --wheel-dir /tmp/python-wheels -r requirements.txt

FROM metabrainz-python-base AS metabrainz-base

COPY requirements.txt /code/metabrainz
COPY --from=metabrainz-python-deps /tmp/python-wheels /tmp/python-wheels
RUN pip install --no-cache-dir --no-deps /tmp/python-wheels/*.whl \
     && rm -rf /tmp/python-wheels

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

COPY webpack.config.js babel.config.js tsconfig.json eslint.config.mjs .stylelintrc.js /code/


#########################################################################
# NOTE: The javascript files for production are compiled in this image. #
#########################################################################
FROM metabrainz-frontend-dev AS metabrainz-frontend-prod

# Compile front-end (static) files
COPY ./frontend /code/frontend
COPY ./metabrainz/translations /code/metabrainz/translations
RUN npm run build:i18n
RUN npm run build:prod


###########################################
# NOTE: The production image starts here. #
###########################################
FROM metabrainz-python-base AS metabrainz-uwsgi-deps

RUN apt-get update \
     && apt-get install -y --no-install-recommends \
                        build-essential \
     && rm -rf /var/lib/apt/lists/*

RUN pip wheel --no-cache-dir --wheel-dir /tmp/uwsgi-wheels uWSGI==2.0.31

FROM metabrainz-base AS metabrainz-prod

COPY --from=metabrainz-uwsgi-deps /tmp/uwsgi-wheels /tmp/uwsgi-wheels
RUN pip install --no-cache-dir /tmp/uwsgi-wheels/*.whl \
     && rm -rf /tmp/uwsgi-wheels

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

COPY ./docker/webhook-worker/consul-template-webhook-worker.conf /etc/
COPY ./docker/webhook-worker/webhook-worker.service /etc/service/webhook-worker/run
RUN chmod 755 /etc/service/webhook-worker/run
RUN touch /etc/service/webhook-worker/down

COPY ./docker/webhook-maintenance/consul-template-webhook-maintenance.conf /etc/
COPY ./docker/webhook-maintenance/webhook-maintenance.service /etc/service/webhook-maintenance/run
RUN chmod 755 /etc/service/webhook-maintenance/run
RUN touch /etc/service/webhook-maintenance/down

COPY ./docker/webhook-beat/consul-template-webhook-beat.conf /etc/
COPY ./docker/webhook-beat/webhook-beat.service /etc/service/webhook-beat/run
RUN chmod 755 /etc/service/webhook-beat/run
RUN touch /etc/service/webhook-beat/down

COPY ./docker/rc.local /etc/rc.local

# copy the compiled js files and static assets from image to prod
COPY --from=metabrainz-frontend-prod /code/frontend/robots.txt /static/
COPY --from=metabrainz-frontend-prod /code/frontend/fonts /static/fonts
COPY --from=metabrainz-frontend-prod /code/frontend/img /static/img
COPY --from=metabrainz-frontend-prod /code/frontend/js/lib /static/js/lib
COPY --from=metabrainz-frontend-prod /code/frontend/dist /static/dist
COPY --from=metabrainz-frontend-prod /code/frontend/locales /static/locales

# Now install our code, which may change frequently
COPY . /code/metabrainz/

# Compile the backend translation catalogs (.mo files for Flask-Babel).
RUN pybabel compile -d /code/metabrainz/metabrainz/translations

# Ensure we use the right files and folders by removing duplicates
RUN rm -rf ./frontend/
RUN rm -f /code/metabrainz/metabrainz/config.py /code/metabrainz/metabrainz/config.pyc

EXPOSE 13031

ARG GIT_COMMIT_SHA
LABEL org.label-schema.vcs-ref=$GIT_COMMIT_SHA
ENV GIT_SHA=${GIT_COMMIT_SHA}
