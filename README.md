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

The app configuration must be stored in the file called `config.py`.
You can use an example one (`config.py.example`) and tweak the
configuration:

    $ cp config.py.example config.py
    $ vim config.py

You need to make sure that required variables are set.

#### MusicBrainz OAuth

To allow users to log in, you'll need to set two keys: ``MUSICBRAINZ_CLIENT_ID``
and ``MUSICBRAINZ_CLIENT_SECRET``. To obtain these keys, you need to register
your instance of MetaBrainz.org on MusicBrainz at
https://musicbrainz.org/account/applications/register. Set Callback URL field
to ``http://<your host>/login/musicbrainz/post`` (if ``PREFERRED_URL_SCHEME``
in the config file is set to ``https``, make sure that you specify the same
protocol for callback URL). If you run the server locally, replace ``<your host>``
with ``localhost``.

#### Payments

Next is the configuration of the payment systems. We use PayPal and Stripe to accept
payments to our foundation. *PAYPAL_ACCOUNT_IDS* dictionary contains PayPal IDs or
email addresses of accounts for each supported currency. *PAYPAL_BUSINESS* is
an address for non-donations; all payments sent there will be ignored.

After these settings have been set and you are sure that your configuration
is working properly within test mode, you can flip the switch. Set *DEBUG* to
``False`` and *PAYMENT_PRODUCTION* to ``True``. **WARNING! For development
purposes, you should only use payments in debug mode.**

#### Serving replication packets

Replication packets must be copied into ``./data/replication_packets`` directory.
It must have the following structure:
```
./data/replication_packets/
    - hourly replication packets
```

### Startup

This command will build and start all the services that you will be able to
use for development:

    $ ./develop.sh

The first time you set up the application, the database needs to be initialized:

    $ ./develop.sh manage init_db --create-db

The web server should now be accessible at **http://localhost:80/**.


### Building style sheets

Due to the way development environment works with Docker, it's necessary to build CSS
separately from building an image. To do that you need to start the development server
(all the containers with Docker Compose) and attach to the `web` container:
```bash
$ ./develop.sh exec -it web bash
```

Then install npm modules and build CSS:
```bash
web# npm install
web# ./node_modules/.bin/lessc ./metabrainz/static/css/main.less > ./metabrainz/static/css/main.css
web# ./node_modules/.bin/lessc ./metabrainz/static/css/theme/boostrap/boostrap.less > ./metabrainz/static/css/theme/boostrap/boostrap.css
web# ./node_modules/.bin/lessc ./metabrainz/static/fonts/font_awesome/less/font-awesome.less > ./metabrainz/static/fonts/font_awesome/less/font-awesome.css
```

*Last two builds are necessary only if you are planning to use the admin interface.*


## Translations

### Extracting strings

Once you have built and started all the services as mentioned above, run:

`$ ./develop.sh manage extract_strings`

### Compiling the strings

The POT files are compiled automatically every time the services are built, but in case you make any changes to the POT files
and want to compile the translation files again, run:

`$ ./develop.sh manage compile_translations`


## Testing

To run all tests use:

    $ ./test.sh

### Testing payments

Before doing anything make sure that the `PAYMENT_PRODUCTION` variable in
the configuration file is set to `False`! This way you'll use testing environments
where credit cards and bank accounts are not actually charged. More info about
testing environments for each payment service can be found in their documentation:

* PayPal: https://developer.paypal.com/webapps/developer/docs/
* Stripe: https://stripe.com/docs/testing

Please note that for [IPNs](https://en.wikipedia.org/wiki/Instant_payment_notification)
to work, the application MUST be publicly available. If you are doing development
on your local machine it is likely that your callback endpoints will not be
reachable for payment processors.
