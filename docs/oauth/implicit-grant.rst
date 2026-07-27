Implicit grant
==============

.. warning::

   The Implicit grant (:rfc:`6749#section-4.2`) is supported for backwards
   compatibility only and is **discouraged for new applications**. Because the
   access token is returned directly in the browser (in the redirect URL
   fragment), it is more exposed than in the Authorization Code flow. New
   single-page and native applications should use the
   :doc:`Authorization Code grant <authorization-code-grant>` with PKCE
   instead, as recommended by the
   `OAuth 2.0 Security Best Current Practice
   <https://datatracker.ietf.org/doc/html/draft-ietf-oauth-security-topics>`_.

In the Implicit grant, the token is issued straight from the authorization
endpoint without a separate token-exchange step.

Authorization request
---------------------

.. http:get:: /oauth2/authorize
   :noindex:

   :query response_type: **Required.** ``token`` for an OAuth access token, or
      ``id_token token`` / ``id_token`` when using OpenID Connect.
   :query client_id: **Required.** Your application's client identifier.
   :query redirect_uri: **Required.** Must exactly match a registered redirect
      URI.
   :query scope: **Required.** Space-separated list of :doc:`scopes <scopes>`.
   :query state: **Recommended.** Opaque anti-CSRF value, returned unchanged.
   :query nonce: **Required with the** ``openid`` **scope.** Random value bound
      to the ID token.
   :query response_mode: Optional. When omitted, the token is returned in the
      URL ``fragment``. The only accepted explicit value is ``form_post``,
      which returns an auto-submitting HTML form that ``POST``\ s the response
      to your ``redirect_uri``; any other value is rejected with
      ``invalid_request``.

Example:

.. code-block:: text

   https://metabrainz.org/oauth2/authorize
     ?response_type=token
     &client_id=YOUR_CLIENT_ID
     &redirect_uri=https://example.com/callback
     &scope=profile
     &state=af0ifjsldkj

Response
--------

The user signs in and approves, and the browser is redirected with the token in
the URL **fragment** (``#``):

.. code-block:: text

   https://example.com/callback#access_token=b1c2d3...&token_type=Bearer&expires_in=3600&state=af0ifjsldkj

Your in-browser code reads the fragment to extract the token. Verify ``state``
before using the token.

.. note::

   Consent is never auto-approved for the Implicit grant: the user is asked to
   confirm on every authorization, in line with
   :rfc:`6819#section-5.2.3.2`.

``form_post`` response mode
---------------------------

If you pass ``response_mode=form_post``, instead of a fragment redirect the
server returns an HTML page that auto-submits an HTML form containing the
values back to your ``redirect_uri`` via an HTTP ``POST``. This avoids exposing
tokens in the URL and browser history.
