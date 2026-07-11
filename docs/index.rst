MetaBrainz documentation
========================

`MetaBrainz.org <https://metabrainz.org/>`_ is the website for the MetaBrainz
Foundation, the non-profit that supports MusicBrainz, ListenBrainz, BookBrainz,
CritiqueBrainz and the other \*Brainz projects.

Among other things, metabrainz.org is the central **OAuth 2.0 and OpenID
Connect provider** for the MetaBrainz projects. A single MetaBrainz account can
be used to sign in to, and authorize third-party applications against,
MusicBrainz, ListenBrainz, CritiqueBrainz and more.

If you are building an application that needs to authenticate MetaBrainz users
or call a \*Brainz API on their behalf, start with the
:doc:`OAuth 2.0 and OpenID Connect documentation <oauth/index>`.

If you are interested in contributing to metabrainz.org as a developer, see the
:doc:`Developer documentation <developers/devel-env>`.

Contents
--------

.. toctree::
   :maxdepth: 2
   :caption: OAuth 2.0 & OpenID Connect

   oauth/index
   oauth/registration
   oauth/scopes
   oauth/authorization-code-grant
   oauth/implicit-grant
   oauth/client-credentials-grant
   oauth/openid-connect
   oauth/token-endpoints

.. toctree::
   :maxdepth: 2
   :caption: Developer Documentation

   developers/devel-env
