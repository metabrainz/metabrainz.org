Setting up a development environment
====================================

The easiest way to set up the MetaBrainz website for development is to use
`Docker <https://www.docker.com/>`_. Make sure that it is installed on your
machine before following the instructions.

metabrainz.org runs its own user accounts (email/password sign-up with email
verification) and acts as the central OAuth 2.0 and OpenID Connect provider for
the \*Brainz projects. The configuration below reflects that setup.

Configuration
-------------

The app configuration must be stored in the file called ``config.py``. Copy the
example and tweak it::

    $ cp config.py.example config.py
    $ vim config.py

The example file ships with working development defaults for most settings. The
sections below describe the ones you are most likely to touch.

Accounts and sessions
^^^^^^^^^^^^^^^^^^^^^

User accounts, login sessions and verification links are protected by a few
secret keys:

``SECRET_KEY``
    Signs Flask sessions and CSRF tokens. Change it to any random string.

``EMAIL_VERIFICATION_SECRET_KEY``
    Signs the tokens embedded in account-verification and password-reset links.

Sign-up requires the user to confirm their email address, so a working mail
setup is needed for the full flow. The development stack includes a mail
container; ``SMTP_SERVER``, ``SMTP_PORT`` and ``MAIL_FROM_DOMAIN`` are
pre-configured to use it, so verification emails are captured locally rather
than sent to real inboxes.

Sign-up is also protected by `MTCaptcha <https://www.mtcaptcha.com/>`_. Leave
``MTCAPTCHA_PUBLIC_KEY`` / ``MTCAPTCHA_PRIVATE_KEY`` empty during local
development unless you specifically want to exercise the captcha.

OAuth 2.0 / OpenID Connect provider
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

metabrainz.org issues OAuth 2.0 tokens and signs OpenID Connect ID tokens. The
relevant settings are:

``OIDC_JWT_PRIVATE_KEY`` / ``OIDC_JWT_PUBLIC_KEY``
    The EC (P-256, ``ES256``) key pair used to sign and verify ID tokens, as
    JWKs. The public key is what the server publishes at its ``jwks_uri``.

    .. danger::

        ``config.py.example`` ships with a **publicly known** development key
        pair. Never use it in production. Generate your own key pair for any
        deployment, for example with Authlib:

        .. code-block:: python

           from authlib.jose import JsonWebKey

           key = JsonWebKey.generate_key(
               "EC", "P-256", options={"kid": "metabrainz-oauth"}, is_private=True
           )
           print(key.as_dict(is_private=True, alg="ES256", use="sig"))   # OIDC_JWT_PRIVATE_KEY
           print(key.as_dict(is_private=False, alg="ES256", use="sig"))  # OIDC_JWT_PUBLIC_KEY

``OAUTH2_BLUEPRINT_PREFIX``
    The URL prefix the OAuth endpoints are mounted under (``/oauth2`` by
    default).

``OAUTH2_TOKEN_EXPIRES_IN`` / ``OAUTH2_AUTHORIZATION_CODE_EXPIRES_IN``
    Token and authorization-code lifetimes, in seconds.

Per-client privileges
    The Client Credentials grant, the user's "remember me" status in the token
    response, and client-initiated registration requests are gated by
    per-client privileges. These are stored as a bitmap in the
    ``oauth.client.privileges`` column and managed from the *OAuth
    Applications* view in the user-management admin, not via configuration.

Once the server is running you can register your own OAuth applications from
the web UI at ``/profile/applications``, and inspect the provider's metadata at
``/.well-known/openid-configuration``. See the
:doc:`OAuth 2.0 & OpenID Connect documentation <../oauth/index>` for the full
API.

Payments
^^^^^^^^

metabrainz.org accepts donations and supporter payments through PayPal and
Stripe. The ``PAYPAL_ACCOUNT_IDS`` dictionary contains PayPal IDs or email
addresses for each supported currency, ``PAYPAL_BUSINESS`` is an address for
non-donations, and ``STRIPE_KEYS`` holds per-currency Stripe API keys.

Keep ``PAYMENT_PRODUCTION`` set to ``False`` for development so that testing
environments are used and no real card or bank account is charged.

.. warning::

    For development purposes, you should only use payments in debug mode.

Serving replication packets
^^^^^^^^^^^^^^^^^^^^^^^^^^^

metabrainz.org also serves the MusicBrainz replication packets. If you are
working on that feature, replication packets must be copied into the
``./data/replication_packets`` directory::

    ./data/replication_packets/
        - hourly replication packets

Startup
-------

This command will build and start all the services that you will be able to use
for development::

    $ ./develop.sh

The first time you set up the application, the database needs to be
initialized. This creates the main schema together with the ``oauth`` schema
and seeds the built-in OAuth :doc:`scopes <../oauth/scopes>`::

    $ ./develop.sh manage init-db --create-db

The web server should now be accessible at http://localhost:8000/.

Translations
------------

Once the services are running, extract translatable strings with::

    $ ./develop.sh manage extract-strings

Translations are consumed in two forms, both generated from the ``.po``
catalogs in ``metabrainz/translations/``: the backend Flask-Babel ``.mo`` files
and the per-locale frontend JSON catalogs. A single command builds both::

    $ ./develop.sh compile-translations

The production Docker image builds translations automatically.

Testing
-------

To run all tests use::

    $ ./test.sh

Testing payments
^^^^^^^^^^^^^^^^

Before doing anything make sure that the ``PAYMENT_PRODUCTION`` variable in the
configuration file is set to ``False``! This way you'll use testing
environments where credit cards and bank accounts are not actually charged.
More info about testing environments for each payment service can be found in
their documentation:

* PayPal: https://developer.paypal.com/webapps/developer/docs/
* Stripe: https://stripe.com/docs/testing

Please note that for `IPNs
<https://en.wikipedia.org/wiki/Instant_payment_notification>`_ to work, the
application MUST be publicly available. If you are doing development on your
local machine it is likely that your callback endpoints will not be reachable
for payment processors.
