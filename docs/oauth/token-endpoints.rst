UserInfo, introspection & revocation
====================================

Beyond obtaining tokens, the server provides endpoints to read the current
user's identity, inspect a token, and revoke a token.

.. _oauth/token-endpoints-userinfo:

UserInfo
--------

Returns identity information about the user associated with an access token.
Authenticate by sending the access token as a Bearer token.

.. http:get:: /oauth2/userinfo

   :reqheader Authorization: **Required.** ``Bearer <access_token>``.

The endpoint also accepts ``POST``.

Example:

.. code-block:: bash

   curl https://metabrainz.org/oauth2/userinfo \
     -H "Authorization: Bearer b1c2d3..."

Example response:

.. code-block:: json

   {
     "sub": "alice",
     "metabrainz_user_id": 12345,
     "member_since": "2016-03-01T00:00:00+00:00"
   }

* ``sub`` — the user's MetaBrainz username.
* ``metabrainz_user_id`` — the user's numeric MetaBrainz identifier.
* ``member_since`` — ISO 8601 timestamp of when the account was created, or
  ``null``.

Error responses:

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Status
     - Condition
   * - ``401``
     - The ``Authorization`` header is missing or malformed.
   * - ``403``
     - The access token is invalid, expired or revoked.
   * - ``400``
     - The token is not associated with a user (for example, a token issued via
       the :doc:`Client Credentials grant <client-credentials-grant>`).

.. _oauth/token-endpoints-token-introspection:

Token introspection
--------------------

Lets a client determine the state and metadata of a token (:rfc:`7662`). The
requesting client must authenticate.

.. http:post:: /oauth2/introspect

   :form token: **Required.** The access or refresh token to inspect.
   :form token_type_hint: Optional. ``access_token`` or ``refresh_token`` to
      speed up the lookup.
   :reqheader Authorization: **Required.** Client authentication via
      ``client_secret_basic`` (HTTP Basic) or ``client_secret_post`` (form
      fields).

Example:

.. code-block:: bash

   curl -X POST https://metabrainz.org/oauth2/introspect \
     -u "YOUR_CLIENT_ID:YOUR_CLIENT_SECRET" \
     -d token=b1c2d3... \
     -d token_type_hint=access_token

Example response for an active token:

.. code-block:: json

   {
     "active": true,
     "client_id": "SOME_CLIENT_ID",
     "token_type": "Bearer",
     "scope": ["openid", "profile", "musicbrainz:collection"],
     "sub": "alice",
     "metabrainz_user_id": 12345,
     "issued_by": "https://metabrainz.org/",
     "issued_at": 1700000000,
     "expires_at": 1700003600
   }

For a token issued via the Client Credentials grant there is no user, so
``sub`` is the application's name and ``metabrainz_user_id`` is omitted.

If the token is unknown, expired or revoked, the response is simply:

.. code-block:: json

   {
     "active": false
   }

Always check the ``active`` field first; do not rely on any other field when
``active`` is ``false``.

.. _oauth/token-endpoints-token-revocation:

Token revocation
----------------

Revokes an access or refresh token (:rfc:`7009`), for example when a user logs
out or disconnects your application. The requesting client must authenticate.

.. http:post:: /oauth2/revoke

   :form token: **Required.** The access or refresh token to revoke.
   :form token_type_hint: Optional. ``access_token`` or ``refresh_token``.
   :reqheader Authorization: **Required.** Client authentication via
      ``client_secret_basic`` or ``client_secret_post``.

Example:

.. code-block:: bash

   curl -X POST https://metabrainz.org/oauth2/revoke \
     -u "YOUR_CLIENT_ID:YOUR_CLIENT_SECRET" \
     -d token=e4f5g6... \
     -d token_type_hint=refresh_token

A successful revocation returns ``HTTP 200`` with an empty body.

.. note::

   **Revoking a refresh token also revokes the access tokens issued alongside
   it** (for the same client and user), as required by :rfc:`7009`. If you only
   revoke an access token, any refresh token remains valid and can still be
   used to obtain new access tokens — revoke the refresh token to fully
   disconnect.
