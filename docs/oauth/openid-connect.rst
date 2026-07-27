OpenID Connect
==============

MetaBrainz is an OpenID Connect (OIDC) provider layered on top of the OAuth 2.0
server. Use OIDC when you want to **authenticate** a user ("Log in with
MetaBrainz") and learn who they are, rather than only obtaining API access.

To enable it, include the ``openid`` scope in an
:doc:`Authorization Code <authorization-code-grant>` (or
:doc:`Implicit <implicit-grant>`) request. In return you receive an **ID
token** — a signed JWT asserting the user's identity — alongside the access
token.

.. code-block:: text

   scope=openid profile

Requesting ``profile`` in addition to ``openid`` controls the release of the
user's public account information. (The ``email`` scope is not yet implemented;
the email address is not currently returned — see :doc:`scopes`.)

.. _oauth/openid-connect-discovery:

Discovery
---------

The provider publishes its configuration as an OpenID Connect Discovery
document. Fetch it and read endpoint URLs and capabilities from it rather than
hard-coding them:

.. http:get:: /.well-known/openid-configuration

Example response:

.. code-block:: json

   {
     "issuer": "https://metabrainz.org",
     "authorization_endpoint": "https://metabrainz.org/oauth2/authorize",
     "token_endpoint": "https://metabrainz.org/oauth2/token",
     "userinfo_endpoint": "https://metabrainz.org/oauth2/userinfo",
     "jwks_uri": "https://metabrainz.org/.well-known/jwks.json",
     "scopes_supported": ["openid", "profile", "email", "musicbrainz:tag", "..."],
     "response_types_supported": ["code", "id_token token", "id_token"],
     "response_modes_supported": ["query", "fragment", "form_post"],
     "grant_types_supported": ["authorization_code", "refresh_token", "implicit"],
     "id_token_signing_alg_values_supported": ["ES256", "none"],
     "subject_types_supported": ["public"]
   }

The ``issuer`` is ``https://metabrainz.org``. This is the value you must match
against the ``iss`` claim of ID tokens.

The ID token
------------

The ID token is a JSON Web Token (JWT) signed with **ES256** (ECDSA using
P-256 and SHA-256). It contains claims such as:

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Claim
     - Meaning
   * - ``iss``
     - Issuer — always ``https://metabrainz.org``.
   * - ``sub``
     - Subject — the user's stable MetaBrainz user id, encoded as a string.
       This is the same value returned as ``sub`` by the
       :ref:`UserInfo endpoint <oauth/token-endpoints:userinfo>`, so the two can
       be compared safely.
   * - ``aud``
     - Audience — your ``client_id``.
   * - ``exp``
     - Expiration time (one hour after issuance).
   * - ``iat``
     - Time the token was issued.
   * - ``nonce``
     - The ``nonce`` value from your authorization request, echoed back.
   * - ``username``
     - The user's MetaBrainz username.

Validating the ID token
------------------------

Before trusting an ID token you **must** validate it:

#. **Verify the signature** using the provider's public key from the
   ``jwks_uri`` (see below). The algorithm is ``ES256``.
#. **Check ``iss``** equals ``https://metabrainz.org``.
#. **Check ``aud``** equals your ``client_id``.
#. **Check ``exp``** is in the future (the token has not expired).
#. **Check ``nonce``** equals the value you sent in the authorization request.
   A ``nonce`` is required for the Authorization Code + OpenID flow specifically
   to let you detect replay — reject the token if it does not match.

Most OpenID Connect client libraries perform these checks for you when given
the discovery document; prefer a well-tested library over hand-rolling JWT
validation.

Signing keys (JWKS)
-------------------

The public keys used to verify ID token signatures are published as a JSON Web
Key Set at the ``jwks_uri`` advertised in the discovery document:

.. http:get:: /.well-known/jwks.json

Example response:

.. code-block:: json

   {
     "keys": [
       {
         "alg": "ES256",
         "kty": "EC",
         "use": "sig",
         "crv": "P-256",
         "kid": "...",
         "x": "...",
         "y": "..."
       }
     ]
   }

Match the ID token header's ``kid`` to the corresponding key in this set. Keys
may be rotated, so fetch the JWKS dynamically and cache it rather than pinning a
single key.

Getting user identity
----------------------

Two complementary ways to obtain the user's identity:

* **ID token claims** — available immediately from the token response, after
  validation, without an extra request.
* **UserInfo endpoint** — call the
  :ref:`UserInfo endpoint <oauth/token-endpoints:userinfo>` with the access
  token to retrieve identity information as JSON.
