Scopes
======

Scopes describe the access your application is requesting. You pass a
space-separated list of scopes in the ``scope`` parameter of an authorization
request, and the user sees a plain-language description of each one on the
consent screen.

Request the **minimum** set of scopes your application actually needs. Users are
more likely to approve a narrow request, and it limits the impact if a token is
ever compromised.

Available scopes
----------------

The set of scopes supported by the server is also published, at runtime, in the
``scopes_supported`` field of the
:ref:`discovery document <oauth/openid-connect:discovery>`.

Identity
^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 25 40 35

   * - Scope
     - Grants access to
     - Shown to the user as
   * - ``openid``
     - Enables OpenID Connect and returns an ID token identifying the user. See
       :doc:`openid-connect`.
     - *Sign you in and view your unique user id*
   * - ``profile``
     - The user's public account information.
     - *View your public account information*
   * - ``email``
     - The user's email address. **Not currently implemented** (see note below).
     - *View your email address*

MusicBrainz
^^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 30 40 30

   * - Scope
     - Grants access to
     - Shown to the user as
   * - ``musicbrainz:tag``
     - View and modify the user's private tags.
     - *View and modify your private tags*
   * - ``musicbrainz:rating``
     - View and modify the user's private ratings.
     - *View and modify your private ratings*
   * - ``musicbrainz:collection``
     - View and modify the user's private collections.
     - *View and modify your private collections*
   * - ``musicbrainz:submit_isrc``
     - Submit new ISRCs to the database.
     - *Submit new ISRCs to the database*
   * - ``musicbrainz:submit_barcode``
     - Submit new barcodes to the database.
     - *Submit new barcodes to the database*

ListenBrainz
^^^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 30 40 30

   * - Scope
     - Grants access to
     - Shown to the user as
   * - ``listenbrainz:submit-listens``
     - Submit listens to ListenBrainz.
     - *Submit listens to ListenBrainz.*

CritiqueBrainz
^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 30 40 30

   * - Scope
     - Grants access to
     - Shown to the user as
   * - ``critiquebrainz:review``
     - Create and modify CritiqueBrainz reviews.
     - *Create and modify CritiqueBrainz reviews.*
   * - ``critiquebrainz:vote``
     - Submit and delete votes on CritiqueBrainz reviews.
     - *Submit and delete votes on CritiqueBrainz reviews.*
   * - ``critiquebrainz:profile``
     - Modify profile info and delete profile on CritiqueBrainz.
     - *Modify profile info and delete profile on CritiqueBrainz.*

Notes
-----

* Scopes are validated against this list. Requesting an unknown scope causes the
  authorization request to fail with ``invalid_scope``.
* Include ``openid`` whenever you want to authenticate the user and receive an
  :doc:`ID token <openid-connect>`. ``profile`` controls the release of the
  user's public account information.
* The ``email`` scope can be requested and approved, but it is **not yet
  implemented**: the user's email address is not currently returned by the
  :ref:`UserInfo endpoint <oauth/token-endpoints:userinfo>` or included in the
  ID token. Do not rely on it to obtain an email address.
* The access token issued to your application carries exactly the scopes the
  user approved. You can confirm the scopes on a token using the
  :ref:`introspection endpoint <oauth/token-endpoints:token introspection>`.
