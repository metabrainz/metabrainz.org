FROM debian:jessie

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        postfix \
        rsyslog \
        vim && \
    rm -rf /var/lib/apt/lists/*

COPY ./mailname /etc/mailname

RUN mkdir /code
WORKDIR /code
COPY ./entrypoint.sh /code/entrypoint.sh
RUN chmod +x /code/entrypoint.sh

ENTRYPOINT /code/entrypoint.sh
