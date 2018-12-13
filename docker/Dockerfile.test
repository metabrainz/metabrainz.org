FROM metabrainz/python:3.6-1

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

ENV DOCKERIZE_VERSION v0.2.0
RUN wget https://github.com/jwilder/dockerize/releases/download/$DOCKERIZE_VERSION/dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz \
    && tar -C /usr/local/bin -xzvf dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz

RUN mkdir /code
WORKDIR /code

COPY requirements.txt /code/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /code/

CMD dockerize -wait tcp://db_test:5432 -timeout 60s \
    py.test --junitxml=/data/test_report.xml \
            --cov-report xml:/data/coverage.xml \
            --cov-report html:/data/coverage-html
