.. _oauth/registration-client-initiated-user-registration:

Client-initiated user registration requests
===========================================

Some trusted clients can start a MetaBrainz account registration flow from
their own application and then continue directly into the Authorization Code
grant. This is intended for clients that have already collected or allocated a
username and email address and want MetaBrainz to create the account, sign the
user in, and return an OAuth authorization code for the same browser session.

This endpoint is restricted. Your ``client_id`` must be listed in
``OAUTH2_REGISTRATION_REQUEST_CLIENTS`` by the MetaBrainz OAuth provider before
you can create registration requests.

Overview
--------

.. code-block:: text

   +--------+                                             +---------------+
   | Client |--(1) registration request + client auth ---->|               |
   | server |<-(2) request_id + redirect_to ---------------|               |
   +--------+                                             |    MetaBrainz |
        |                                                 | authorization |
        | (3) send the user's browser to redirect_to       |    server     |
        v                                                 |               |
   +---------+--(4) signup or login, then consent -------->|               |
   | Browser |<-(5) authorization code to redirect_uri ----|               |
   +---------+                                             +---------------+
        |
        | (6) client backend exchanges the code for tokens
        v
   +--------+
   | Client |
   +--------+

The registration request does not replace the Authorization Code grant. It
creates a short-lived browser handoff that pre-fills MetaBrainz signup details
and then resumes the normal authorization flow.

Step 1 - Create the registration request
----------------------------------------

From your backend, post to the registration request endpoint. The client must
authenticate with ``client_secret_basic`` (HTTP Basic) or
``client_secret_post`` (form fields).

.. http:post:: /oauth2/registration-requests

   :form username: **Required.** Requested MetaBrainz username. The value must
      pass normal username validation and must not already be in use.
   :form email: **Required.** Requested email address. The value is normalized,
      must pass normal email validation, must not already be in use, and must
      not be from a blocked domain.
   :form redirect_uri: **Required.** The OAuth callback URL that will receive
      the authorization code. It must exactly match one of the redirect URIs
      registered for your client.
   :form scope: **Required.** Space-separated list of requested OAuth scopes.
   :form state: **Required.** Opaque value returned unchanged to your
      ``redirect_uri``. Use it to bind the result to your local flow and to
      prevent CSRF.
   :form code_challenge: **Required.** PKCE code challenge for the authorization
      code that will be issued later.
   :form code_challenge_method: Optional. Use ``S256``. If omitted, the server
      currently defaults to ``plain``, which is not recommended.
   :form response_type: Optional. Only ``code`` is supported; when omitted, it
      defaults to ``code``.
   :form nonce: Required when requesting the ``openid`` scope.
   :form response_mode: Optional. Same behavior as the authorization endpoint;
      use ``form_post`` if you need the authorization response posted to your
      ``redirect_uri``.
   :reqheader Authorization: Client authentication when using
      ``client_secret_basic``. Alternatively, send ``client_id`` and
      ``client_secret`` as form fields.

The registration request endpoint validates the supplied OAuth parameters
before storing the request. It also forces the eventual authorization request
to use ``approval_prompt=force`` and ``login_hint=register``.

Example:

.. code-block:: bash

   curl -X POST https://metabrainz.org/oauth2/registration-requests \
     -u "YOUR_CLIENT_ID:YOUR_CLIENT_SECRET" \
     -d username=alice \
     -d email=alice@example.com \
     -d redirect_uri=https://example.com/callback \
     -d scope="profile" \
     -d state=af0ifjsldkj \
     -d code_challenge=E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM \
     -d code_challenge_method=S256

Successful response:

.. code-block:: json

   {
     "request_id": "mebrq_...",
     "redirect_to": "https://metabrainz.org/oauth2/registration-requests/mebrq_...",
     "expires_in": 300
   }

The response status is ``201 Created`` and the ``Location`` header is set to
the same URL as ``redirect_to``. ``expires_in`` is in seconds; registration
requests currently expire after 5 minutes by default.

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
     - The client is not whitelisted for registration requests.
   * - ``400``
     - ``invalid_request``
     - A required field is missing, the username or email cannot be used, the
       redirect URI is not registered, or another authorization parameter is
       invalid.
   * - ``400``
     - ``invalid_scope``
     - The requested scope is not supported.

Step 2 - Redirect the browser
-----------------------------

Send the user's browser to the ``redirect_to`` URL. Do not treat this URL as a
server-to-server API URL; it is the browser entry point for the rest of the
flow.

If the user is not signed in, MetaBrainz redirects them to ``/signup`` with the
registration request attached. The signup form is pre-filled with the supplied
``username`` and ``email``. On form submission, MetaBrainz uses the stored
registration request values, not editable browser-submitted replacements, for
the account being created.

The user may also choose to sign in to an existing MetaBrainz account instead
of creating a new account. In that case the supplied ``username`` and ``email``
are only hints for the UI; the OAuth result belongs to the account that signed
in.

If the browser already has an active MetaBrainz session, the signup step is
skipped and the flow proceeds directly to authorization for that signed-in
user.

Step 3 - Complete authorization and exchange the code
-----------------------------------------------------

After signup or login, MetaBrainz resumes the stored authorization request and
shows the consent screen. If the user approves, the browser is redirected to
your ``redirect_uri`` with an authorization code and the original ``state``.
The registration request is consumed when this authorization redirect is
started; expired or already-consumed request URLs show an error.

Exchange the code at ``/oauth2/token`` exactly as described in
:doc:`authorization-code-grant`. Send the same ``redirect_uri`` and the
``code_verifier`` corresponding to the ``code_challenge`` from step 1.

Step 4 - Read the final MetaBrainz identity
-------------------------------------------

After you receive an access token, call the :ref:`UserInfo endpoint
<oauth/token-endpoints:userinfo>` with that access token and use the returned
``sub`` and ``username`` for any internal account linking you need to perform.
Do not rely on the ``username`` or ``email`` supplied to the registration
request as the final MetaBrainz identity: those values may not match the
authorized account if the user chose to log in instead of creating a new
account.

Next steps
----------

Continue with the :doc:`Authorization Code grant <authorization-code-grant>`,
or see :doc:`scopes` to decide what access to request.
