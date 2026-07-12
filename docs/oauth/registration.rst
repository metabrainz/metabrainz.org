Registering an application
==========================

Before you can use any OAuth flow you must register an application with
MetaBrainz. Registration gives you a **client identifier** and, for
confidential clients, a **client secret**.

Applications are managed from your MetaBrainz account, under **Applications**:

    https://metabrainz.org/profile/applications

You need to be signed in to a MetaBrainz account. From this page you can create
new applications, edit or delete existing ones, and revoke access tokens that
you have granted to other applications.

.. figure:: images/01-login.png
   :alt: The MetaBrainz sign-in page
   :align: center
   :width: 100%

   You must sign in to your MetaBrainz account before you can manage
   applications.

The **Applications** tab is empty until you register your first application:

.. figure:: images/02-applications-empty.png
   :alt: The Applications tab with no applications registered
   :align: center
   :width: 100%

   The Applications tab before any application has been registered.

Creating an application
-----------------------

Choose **Create a new application** and fill in the form:

.. figure:: images/03-create-blank.png
   :alt: The blank create-application form
   :align: center
   :width: 100%

   The blank create-application form.

``Application Name``
    A human-readable name for your application (3–64 characters). This is shown
    to users on the consent screen when they authorize your application, so
    choose something recognisable.

``Description``
    A short description of what the application does (3–512 characters). Also
    shown to users.

``Homepage``
    The home page of your application. Must be an ``http://`` or ``https://``
    URL.

``Authorization callback URL``
    One or more URLs the authorization server is allowed to redirect back to
    after the user approves or denies your request. You can add several. This is
    a critical security control:

    * The ``redirect_uri`` sent in an authorization request must **exactly
      match** one of the registered values (scheme, host, port and path).
    * URLs must use ``http`` or ``https``. Use ``https`` in production; plain
      ``http`` is intended only for ``localhost`` redirects during local
      development.
    * Register every environment you need (for example a production and a
      staging callback) as separate callback URLs.

.. figure:: images/04-create-filled.png
   :alt: The create-application form filled in with example values
   :align: center
   :width: 100%

   The create-application form, filled in with an example name, description,
   homepage and callback URL.

After you submit the form, MetaBrainz generates a ``client_id`` and
``client_secret`` for the application and shows them on the applications page.

.. figure:: images/05-applications-list.png
   :alt: The Applications tab listing a registered application
   :align: center
   :width: 100%

   The **Applications** tab. Each application you own is listed with its
   ``client_id`` and (hidden by default) ``client_secret``, alongside
   **Modify** and **Delete** actions.

Editing and deleting
--------------------

.. figure:: images/06-edit.png
   :alt: The edit-application form
   :align: center
   :width: 100%

   Editing an application lets you change its name, description, homepage and
   callback URLs.

From the applications page you can:

* **Edit** an application to change its name, description, homepage or callback
  URLs.
* **Delete** an application. This removes the client; existing tokens issued to
  it stop working.
* **Revoke** the access and refresh tokens that a given application currently
  holds for your account, without deleting the application.

All clients are confidential
----------------------------

Every registered application receives a ``client_secret``, and the token
endpoint **requires** the client to authenticate with it (via
``client_secret_basic`` or ``client_secret_post``; see
:doc:`authorization-code-grant`). There is currently **no support for public
clients** — that is, clients that authenticate without a secret.

This has an important consequence for applications that cannot keep a secret,
such as single-page applications, mobile apps and other native/desktop
software: the ``client_secret`` must never be embedded in code that runs on the
user's device, because it can be extracted. Instead, route the token exchange
(and any token refresh) through a backend component that holds the secret and
proxies requests for your front end. Using :ref:`PKCE
<oauth/authorization-code-grant:proof key for code exchange (pkce)>` is
recommended as an additional protection, but it does **not** replace client
authentication here.

Your credentials
----------------

After registering you will have:

``client_id``
    A public identifier for your application. It is sent in authorization and
    token requests and is not secret.

``client_secret``
    A confidential secret used to authenticate your application at the token
    endpoint. **Store it securely and never expose it in a browser, mobile app,
    or public repository.**

If a secret is ever leaked, delete and re-create the application to obtain new
credentials.

.. _oauth/registration-client-initiated-user-registration:

Client-initiated user registration requests
-------------------------------------------

Some trusted clients can start a MetaBrainz account registration flow from
their own application and then continue directly into the Authorization Code
grant. This is intended for clients that have already collected or allocated a
username and email address and want MetaBrainz to create the account, sign the
user in, and return an OAuth authorization code for the same browser session.

This endpoint is restricted. Your ``client_id`` must be listed in
``OAUTH2_REGISTRATION_REQUEST_CLIENTS`` by the MetaBrainz OAuth provider before
you can create registration requests.

Overview
~~~~~~~~

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
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

After signup or login, MetaBrainz resumes the stored authorization request and
shows the consent screen. If the user approves, the browser is redirected to
your ``redirect_uri`` with an authorization code and the original ``state``.
The registration request is consumed when this authorization redirect is
started; expired or already-consumed request URLs show an error.

Exchange the code at ``/oauth2/token`` exactly as described in
:doc:`authorization-code-grant`. Send the same ``redirect_uri`` and the
``code_verifier`` corresponding to the ``code_challenge`` from step 1.

Step 4 - Read the final MetaBrainz identity
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

After you receive an access token, call the :ref:`UserInfo endpoint
<oauth/token-endpoints:userinfo>` with that access token and use the returned
``sub`` and ``username`` for any internal account linking you need to perform.
Do not rely on the ``username`` or ``email`` supplied to the registration
request as the final MetaBrainz identity: those values may not match the
authorized account if the user chose to log in instead of creating a new
account.

Next steps
----------

Once registered, continue with the :doc:`Authorization Code grant
<authorization-code-grant>`, or see :doc:`scopes` to decide what access to
request.
