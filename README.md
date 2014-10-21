# metabrainz.org

Modern version of the [MetaBrainz Foundation](http://metabrainz.org/) website.
This is a Flask-based web application that is meant to provide info about the
foundation and accept donations from users and organizations.

## Development

Before starting the application copy `config.py.example` into `config.py` and
tweak the configuration.

The easiest way to set up a development environment is to use [Vagrant](https://www.vagrantup.com/).
This command will create and configure virtual machine that you will be able to
use for development:

    $ vagrant up

After VM is created and running, access it via SSH and start the application: 

    $ vagrant ssh
    $ cd /vagrant
    $ python run.py

Web server should be accessible at http://localhost:5000/.

### Testing

To run all tests use:

    $ fab test

This command will run all tests and produce a coverage report in HTML format.
It will be located in cover/index.html file. We use [nose](http://readthedocs.org/docs/nose/)
package to run test cases.

### Testing donations

Before doing anything make sure that `PAYMENT_PRODUCTION` variable in
configuration file is set to `False`! This way you'll use testing environments
where credit cards and bank accounts are not actually charged. More info about
testing environments for each payment service can be found in their documentation:

* WePay: https://www.wepay.com/developer/reference/testing
* PayPal: https://developer.paypal.com/webapps/developer/docs/

Please note that in order for [IPNs](https://en.wikipedia.org/wiki/Instant_payment_notification)
to work, application MUST be publicly available. If you are doing development
on your local machine it is likely that your callback endpoints will not be
reachable from payment processors.

## Installation

If you want to do development you should use instructions above. It is much
easier way to start.

### Prerequisites

1. A Unix based operating system is *recommended*. If you use Windows, you
might encounter some problems with dependencies on specific versions of
compilers. **This tutorial assumes that you use Ubuntu or similar distribution
of Linux.**

2. Python 2.7

3. PostgreSQL (at least version 9.1) + its development libraries
(postgresql-9.x postgresql-server-dev-9.x postgresql-contrib-9.x)

4. Git

5. Standard Development Tools™ (``sudo apt-get install build-essential``)

### Server configuration

1. Download the source code

    $ git clone git://github.com/metabrainz/metabrianz.org.git
    $ cd musicbrainz.org

2. Modify the server configuration file

    $ cp metabrainz/config.py.example metabrainz/config.py

First modify the URI of your primary database (*SQLALCHEMY_DATABASE_URI*).
It should be similar to the provided example. We tested this application with
PostgreSQL and there's no guarantee that it will work with some other DBMS.

Next is configuration of the payment systems. We use PayPal and WePay to accept
donations to our foundation. For WePay you need to set your access token
(*WEPAY_ACCESS_TOKEN*) and account ID (*WEPAY_ACCESS_TOKEN*). PayPal is a
bit more complicated. *PAYPAL_PRIMARY_EMAIL* is an address that should receive
all the payments. *PAYPAL_BUSINESS* is an address for non-donations; all
payments sent there will be ignored.

After these settings have been set and you are sure that your configuration
is working properly with in test mode, you can flip the switch (set *DEBUG* to
``False`` and *PAYMENT_PRODUCTION* to ``True``.

### Python dependencies

There are several packages required to run this application. All are defined in
the *requirements.txt* file. To install them run:

    $ pip install -r requirements.txt

### Database creation

*TO BE WRITTEN*

### Starting the server

You should now have all the necessary pieces together.

The development server is a lightweight HTTP server that gives good debug
output and is much more convenient than having to set up a standalone server.
Just run:

    $ python run.py

Visiting http://127.0.0.1:5000 should now present you with your own running
instance of the MetaBrainz Foundation.

## Community

If you want to discuss something, go to *#musicbrainz-devel* IRC channel on
irc.freenode.net. More info about available methods of getting in touch with
community is available at https://wiki.musicbrainz.org/Communication.

Good luck! You'll need it.
