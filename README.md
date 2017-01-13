# metabrainz.org

**Website for the [MetaBrainz Foundation](https://metabrainz.org/).** This is
a Flask-based web application that provides info about the foundation and its
supporters, accepts donations from users and organizations, and provides
access to the [replication packets](https://musicbrainz.org/doc/Replication_Mechanics)
for MusicBrainz.


## Development setup

The easiest way to set up MetaBrainz website for development is to use
[Docker](https://www.docker.com/). Make sure that it is installed on your
machine before following the instructions.

### Configuration

Custom configuration must be stored in the file called `custom_config.py`.
You can use an example one (`custom_config.py.example`) and tweak the
configuration:

    $ cp custom_config.py.example custom_config.py
    $ vim custom_config.py

You need to make sure that required variables are set.

#### MusicBrainz OAuth

To allow users to log in, you'll need to set two keys: ``MUSICBRAINZ_CLIENT_ID``
and ``MUSICBRAINZ_CLIENT_SECRET``. To obtain these keys, you need to register
your instance of MetaBrainz.org on MusicBrainz at
https://musicbrainz.org/account/applications/register. Set Callback URL field
to ``http://<your host>/login/musicbrainz/post`` (if ``PREFERRED_URL_SCHEME``
in the config file is set to ``https``, make sure that you specify the same
protocol for callback URL). If you run server locally, replace ``<your host>``
with ``localhost``.

#### Payments

Next is the configuration of the payment systems. We use PayPal and WePay to accept
donations to our foundation. For WePay you need to set your access token
(*WEPAY_ACCESS_TOKEN*) and account ID (*WEPAY_ACCESS_TOKEN*). PayPal is a
bit more complicated. *PAYPAL_PRIMARY_EMAIL* is an address that should receive
all the payments. *PAYPAL_BUSINESS* is an address for non-donations; all
payments sent there will be ignored.

After these settings have been set and you are sure that your configuration
is working properly with in test mode, you can flip the switch. Set *DEBUG* to
``False`` and *PAYMENT_PRODUCTION* to ``True``. **WARNING! For development
purposes you should only use payments in debug mode.**

#### Serving replication packets

Replication packets must be copied into ``./data/replication_packets`` directory.
It must have the following structure:
```
./data/replication_packets/
    - hourly replication packets

./data/replication_packets/daily/
    - daily replication packets

./data/replication_packets/weekly/
    - weekly replication packets
```

### Startup

This command will build and start all the services that you will be able to
use for development:

    $ docker-compose -f docker/docker-compose.dev.yml up --build -d

The first time you set up the application, database tables need to be created:

    $ docker-compose -f docker/docker-compose.dev.yml run web python manage.py create_tables

Web server should now be accessible at **http://localhost:80/**.

## Translations

### Extracting strings

Once the docker is up, run:

`$ docker-compose -f docker/docker-compose.dev.yml run web python manage.py extract_strings`

### Compiling the strings

The POT files are compiled automatically every time the docker is created, but in case you make any changes
and want to compile the translations files again, run:

`$ docker-compose -f docker/docker-compose.dev.yml run web python manage.py compile_translations`

## Testing

To run all tests use:

    $ py.test
    
or with Docker:

    $ docker-compose -f docker/docker-compose.test.yml up --build --remove-orphans

### Testing donations

Before doing anything make sure that `PAYMENT_PRODUCTION` variable in
configuration file is set to `False`! This way you'll use testing environments
where credit cards and bank accounts are not actually charged. More info about
testing environments for each payment service can be found in their documentation:

* WePay: https://www.wepay.com/developer/reference/testing
* PayPal: https://developer.paypal.com/webapps/developer/docs/
* Stripe: https://stripe.com/docs/testing

Please note that in order for [IPNs](https://en.wikipedia.org/wiki/Instant_payment_notification)
to work, application MUST be publicly available. If you are doing development
on your local machine it is likely that your callback endpoints will not be
reachable from payment processors.
