Client Credentials grant
========================

The Client Credentials grant (:rfc:`6749#section-4.4`) lets a confidential
client obtain an access token for itself, with **no user involved**. Use it for
machine-to-machine access where your application acts on its own behalf rather
than on behalf of an end user.

.. important::

   This grant is **restricted**. Only clients that MetaBrainz has granted the
   *Client credentials grant* privilege may use it. A client without that
   privilege receives an ``unauthorized_client`` error even with valid
   credentials. If your integration needs client-credentials access, contact
   MetaBrainz.

Token request
-------------

.. http:post:: /oauth2/token
   :noindex:

   :form grant_type: **Required.** Must be ``client_credentials``.
   :form scope: Requested :doc:`scopes <scopes>`.
   :reqheader Authorization: Client authentication. Use HTTP Basic auth with
      ``client_id:client_secret`` (``client_secret_basic``), or send
      ``client_id`` and ``client_secret`` as form fields
      (``client_secret_post``).

Example:

.. code-block:: bash

   curl -X POST https://metabrainz.org/oauth2/token \
     -u "YOUR_CLIENT_ID:YOUR_CLIENT_SECRET" \
     -d grant_type=client_credentials \
     -d scope=musicbrainz:submit_isrc

Response
--------

.. code-block:: json

   {
     "access_token": "b1c2d3...",
     "token_type": "Bearer",
     "expires_in": 3600,
     "scope": "musicbrainz:submit_isrc"
   }

The access token is **not associated with any user**. No refresh token is
issued — request a new token when the current one expires. When you
:ref:`introspect <oauth/token-endpoints:token introspection>` such a token, its
``sub`` is ``"-1"`` and no ``username`` is present.
