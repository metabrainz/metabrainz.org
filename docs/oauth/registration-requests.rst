.. _oauth/registration-client-initiated-user-registration:

Client-initiated user registration requests
===========================================

Trusted clients can provision MetaBrainz accounts from their backend. The
client supplies a username, email address, and optionally its trusted email
confirmation status and OAuth scopes. MetaBrainz creates an account without a
password and sends a welcome email containing the OAuth client's name,
description, the exact scopes granted (or that none were granted), and a link
for the user to choose a password. The welcome email is always sent, since it
carries the only link with which the user can set a password. The link verifies
an unconfirmed email address and expires after seven days. When scopes are
requested, the response includes access and refresh tokens for the new user.

This endpoint is restricted. Your client must be granted the *Registration
requests* privilege by the MetaBrainz OAuth provider before it can create
accounts.

Create an account
-----------------

The request must be made from the client backend. Authenticate using
``client_secret_basic`` (HTTP Basic). Never expose the client secret in a
browser or mobile application.

.. http:post:: /oauth2/registration-requests

   :json string username: **Required.** The requested MetaBrainz username. It must
      pass normal username validation and must not already be in use.
   :json string email: **Required.** The user's email address. It is normalized, must
      pass normal email validation, must not already be in use by another
      account, whether confirmed or pending and matched case insensitively, and
      must not be from a blocked domain.
   :json boolean email_confirmed: Optional. Set to ``true`` if your trusted
      backend has already confirmed that the email belongs to the user.
      Defaults to ``false``.
   :json string scope: Optional. A space-separated list of OAuth scopes to
      grant to the requesting client for the newly created user. Unknown scopes
      are rejected, and so is ``openid``: this endpoint issues the token
      directly and cannot return an ID token. Restricted scopes are accepted
      only when they have been granted to the OAuth client by the MetaBrainz
      OAuth provider.
   :reqheader Authorization: **Required.** HTTP Basic client authentication.
   :reqheader Content-Type: **Required.** ``application/json``.

Only a JSON object is accepted as the request body. Form-encoded requests and
client credentials in the JSON body are rejected.

Example:

.. code-block:: bash

   curl -X POST https://metabrainz.org/oauth2/registration-requests \
     -u "YOUR_CLIENT_ID:YOUR_CLIENT_SECRET" \
     -H "Content-Type: application/json" \
     -d '{"username": "alice", "email": "alice@example.com", "email_confirmed": true, "scope": "profile email"}'

Successful response:

.. code-block:: json

   {
     "user_id": 123,
     "username": "alice",
     "email": "alice@example.com",
     "email_confirmed": true,
     "token_type": "Bearer",
     "access_token": "ACCESS_TOKEN",
     "expires_in": 3600,
     "refresh_token": "REFRESH_TOKEN",
     "scope": "profile email"
   }

The response status is ``201 Created``. The account cannot be used for
password authentication until the user follows the link in the welcome email
and chooses a password. The setup link is single-use and expires after seven
days. It confirms the address during setup only when ``email_confirmed`` was
false or omitted.

Subscribers to the ``user.created`` webhook event receive it for the new
account; the event carries no email address. The address is announced with a
``user.updated`` event instead, emitted when the user confirms it during setup,
or immediately after ``user.created`` when ``email_confirmed`` was true and
there is nothing left for the user to confirm.

When ``scope`` is omitted, no OAuth tokens are issued and the response contains
only ``user_id``, ``username``, ``email``, and ``email_confirmed``. Access and
refresh tokens are credentials and must be stored securely. The refresh token
can be used at the normal token endpoint to obtain new access tokens.

Common errors:

.. list-table::
   :header-rows: 1
   :widths: 20 25 55

   * - Status
     - Error
     - Condition
   * - ``401``
     - ``invalid_client``
     - Client authentication failed.
   * - ``403``
     - ``unauthorized_client``
     - The client lacks the *Registration requests* privilege.
   * - ``400``
     - ``invalid_request``
     - The body is not a JSON object, a required field is missing,
       ``username``, ``email``, or ``scope`` has the wrong type,
       ``email_confirmed`` is not a boolean, or the username or email cannot be
       used.
   * - ``400``
     - ``invalid_scope``
     - A requested scope is unknown, is ``openid``, or is restricted and has
       not been granted to the OAuth client.

After account setup
-------------------

The user can sign in normally after choosing a password. If the provisioning
request did not include ``scope``, start the normal :doc:`Authorization Code
grant <authorization-code-grant>` when the application later needs the user to
authorize access.
