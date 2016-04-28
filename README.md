# metabrainz.org

Website for the [MetaBrainz Foundation](http://metabrainz.org/). This is
a Flask-based web application that is meant to provide info about the
foundation, accept donations from users and organizations, and provide
access to [replication packets](https://musicbrainz.org/doc/Replication_Mechanics)
for MusicBrainz.

## Development

Before starting the application copy `config.py.example` into `config.py` 
(in the metabrainz directory) and tweak the configuration. You need to make sure 
that all API keys are set.

The easiest way to set up a development environment is to use [Vagrant](https://www.vagrantup.com/).
This command will create and configure virtual machine that you will be able to
use for development:

    $ vagrant up

After VM is created and running, access it via SSH and start the application: 

    $ vagrant ssh
    $ cd /vagrant
    $ python manage.py runserver -d

Web server should be accessible at http://localhost:8080/.

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
* Stripe: https://stripe.com/docs/testing

Please note that in order for [IPNs](https://en.wikipedia.org/wiki/Instant_payment_notification)
to work, application MUST be publicly available. If you are doing development
on your local machine it is likely that your callback endpoints will not be
reachable from payment processors.

## Deployment

*If you want to do development you should use instructions above. It is much
easier way to start.*

For more detailed installation instructions see [INSTALL.md](https://github.com/metabrainz/metabrainz.org/blob/master/INSTALL.md)
file.

## Community

If you want to discuss something, go to *#metabrainz* IRC channel on
irc.freenode.net. More info about available methods of getting in touch with
community is available at https://wiki.musicbrainz.org/Communication.

Good luck! You'll need it.
