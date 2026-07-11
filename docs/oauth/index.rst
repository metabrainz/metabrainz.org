OAuth 2.0 & OpenID Connect
==========================

MetaBrainz runs a single OAuth 2.0 authorization server and OpenID Connect
provider that is shared across the \*Brainz projects. Users have one MetaBrainz
account, and your application can use it to:

* **Sign users in** ("Log in with MetaBrainz") using OpenID Connect, and
* **Call \*Brainz APIs on a user's behalf** (for example, submit listens to
  ListenBrainz or edit a MusicBrainz collection) using OAuth 2.0 access tokens.

The server implements the relevant parts of the following specifications:

* :rfc:`6749` – The OAuth 2.0 Authorization Framework
* :rfc:`6750` – Bearer Token Usage
* :rfc:`7636` – Proof Key for Code Exchange (PKCE)
* :rfc:`7009` – Token Revocation
* :rfc:`7662` – Token Introspection
* `OpenID Connect Core 1.0 <https://openid.net/specs/openid-connect-core-1_0.html>`_
  and `Discovery 1.0 <https://openid.net/specs/openid-connect-discovery-1_0.html>`_

Endpoints
---------

All endpoints are served from ``https://metabrainz.org``. The exact URLs are
also published in the :ref:`discovery document
<oauth/openid-connect:discovery>`, which you should treat as the source of
truth. As of writing they are:

.. list-table::
   :header-rows: 1
   :widths: 30 20 50

   * - Endpoint
     - Method
     - URL
   * - Authorization
     - ``GET``
     - ``https://metabrainz.org/oauth2/authorize``
   * - Token
     - ``POST``
     - ``https://metabrainz.org/oauth2/token``
   * - Token revocation
     - ``POST``
     - ``https://metabrainz.org/oauth2/revoke``
   * - Token introspection
     - ``POST``
     - ``https://metabrainz.org/oauth2/introspect``
   * - UserInfo
     - ``GET`` / ``POST``
     - ``https://metabrainz.org/oauth2/userinfo``
   * - Discovery metadata
     - ``GET``
     - ``https://metabrainz.org/.well-known/openid-configuration``
   * - JWKS (signing keys)
     - ``GET``
     - see ``jwks_uri`` in the discovery document

.. note::

   The token issuer — the ``iss`` claim in ID tokens and the OpenID
   ``issuer`` — is ``https://metabrainz.org``. This is the value you match when
   validating ID tokens.

Which grant should I use?
-------------------------

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Application type
     - Recommended flow
   * - Web app with a backend that can keep a secret
     - :doc:`Authorization Code grant <authorization-code-grant>` (with PKCE)
   * - Single-page app / mobile / native
     - :doc:`Authorization Code grant <authorization-code-grant>` with the token
       exchange proxied through your backend (see note below)
   * - Machine-to-machine, no user involved
     - :doc:`Client Credentials grant <client-credentials-grant>`
       (must be whitelisted)
   * - Legacy in-browser client
     - :doc:`Implicit grant <implicit-grant>` (discouraged)

.. note::

   Every registered client is **confidential**: it receives a
   ``client_secret`` and must authenticate with it at the token endpoint. The
   server does not currently support public (secret-less) clients. Applications
   that cannot keep a secret — single-page, mobile and native apps — must
   perform the token exchange from a backend component rather than directly
   from the user's device. See :doc:`registration`.

For "Log in with MetaBrainz" / retrieving the user's identity, use the
Authorization Code grant together with the ``openid`` scope and read
:doc:`openid-connect`.

.. warning::

   The Implicit grant is supported for backwards compatibility only. New
   applications — including single-page and native apps — should use the
   Authorization Code grant with PKCE, per the
   `OAuth 2.0 Security Best Current Practice
   <https://datatracker.ietf.org/doc/html/draft-ietf-oauth-security-topics>`_.

Getting started
---------------

#. :doc:`Register an application <registration>` to obtain a ``client_id`` and
   a ``client_secret``.
#. Decide which :doc:`scopes <scopes>` your application needs.
#. Send the user through the :doc:`Authorization Code grant
   <authorization-code-grant>` to obtain an access token (and optionally an ID
   token and refresh token).
#. Use the access token as a Bearer token when calling \*Brainz APIs.

Security model
--------------

All OAuth endpoints send ``Cache-Control: no-store``, ``Pragma: no-cache``,
``X-Frame-Options: DENY`` and ``Referrer-Policy: no-referrer`` to protect
tokens and the consent screen. Beyond that, applications are expected to follow
current best practice:

* **Always use HTTPS** for your ``redirect_uri`` (except ``http://localhost``
  loopback redirects used during development).
* **Register exact redirect URIs.** The server only redirects to URIs that
  match one of the values registered for your client.
* **Use PKCE** for the Authorization Code grant as an additional protection.
* **Validate the ``state`` parameter** on the redirect to prevent CSRF.
* **Validate the ID token** (signature, ``iss``, ``aud``, ``exp`` and
  ``nonce``) before trusting it. See :doc:`openid-connect`.
* **Keep the client secret confidential.** Never embed it in a browser, mobile
  or native app; perform the token exchange from a backend instead.
