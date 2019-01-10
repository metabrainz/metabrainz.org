FROM metabrainz/python:3.6-1

# PostgreSQL client
ENV PG_MAJOR 9.5
RUN wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add -
RUN echo 'deb http://apt.postgresql.org/pub/repos/apt/ jessie-pgdg main' $PG_MAJOR > /etc/apt/sources.list.d/pgdg.list
RUN apt-get update \
    && apt-get install -y postgresql-client-$PG_MAJOR \
    && rm -rf /var/lib/apt/lists/*
# Specifying password so that client doesn't ask scripts for it...
ENV PGPASSWORD "metabrainz"

RUN mkdir /code
WORKDIR /code

# Node
RUN curl -sL https://deb.nodesource.com/setup_7.x | bash -
RUN apt-get install -y nodejs

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

COPY . /code/
