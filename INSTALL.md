## Installation instructions

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

    $ python manage.py create_db
    $ python manage.py create_tables

### Starting the server

You should now have all the necessary pieces together.

The development server is a lightweight HTTP server that gives good debug
output and is much more convenient than having to set up a standalone server.
Just run:

    $ python run.py

Visiting http://127.0.0.1:5000 should now present you with your own running
instance of the MetaBrainz Foundation.
