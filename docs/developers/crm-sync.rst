Supporter CRM synchronization
============================

Commercial and non-commercial signups queue a Twenty sync after committing.
Pending work is stored in ``crm_sync`` and recovered every five minutes by
Celery Beat. Failed attempts back off up to one hour. Automatic synchronization
currently covers signups only; updates and backfills use the command below.

CRM schema
----------

Create these fields using the exact API names before enabling the integration.

On People:

* ``metabrainzUserId``: nullable unique TEXT.
* ``metabrainzUsername``, ``metabrainzEmail``: TEXT.
* ``metabrainzEmailVerified``: BOOLEAN.

Create custom object ``supporterAccount`` / ``supporterAccounts``:

* ``name``: standard name field.
* ``metabrainzSupporterId``: unique TEXT.
* ``primaryContact``: MANY_TO_ONE relation to People (``primaryContactId``).
* ``company``: optional MANY_TO_ONE relation to Companies (``companyId``).
* ``contactName``, ``tierId``, ``tierName``, ``dataUsageDescription``: TEXT.
* ``isCommercial``, ``goodStanding``: BOOLEAN.
* ``state``: SELECT with values ``ACTIVE``, ``PRE_REVENUE``, ``PENDING``,
  ``WAITING``, ``REJECTED``, ``LIMITED``.
* ``amountPledged``: CURRENCY (USD).
* ``datasets``: TEXT containing a JSON array of dataset IDs and names.
* ``sourceCreatedAt``, ``lastSyncedAt``: DATE_TIME.

Companies use standard fields only. New company domains are stored as lowercase
hostnames without a scheme, port, path or trailing dot, matching the lookup format.

Deployment
----------

1. Apply ``admin/schema_updates/2026-09-23-add-crm-sync.sql``.
2. Create the CRM schema above and an API key for People, Companies and Supporter
   Accounts.
3. Set ``CRM_URL`` (HTTPS origin without ``/rest``), ``CRM_API_KEY``, ``CRM_SOURCE``
   and ``CRM_ENABLED = True``. Production Consul keys are ``crm/url``,
   ``crm/api_key``, ``crm/source`` and ``crm/enabled`` (Python ``True``/``False``).
   Use a separate workspace and source namespace for staging.
4. Run Beat, a maintenance worker consuming ``webhooks_maintenance``, and one CRM
   worker (limited to five supporters per minute)::

       celery -A celery_worker:celery worker --queues=crm --concurrency=1

   The production image enables the Consul-configured CRM worker when
   ``CONTAINER_NAME=metabrainz-crm-worker-${DEPLOY_ENV}``.
   Development Compose enables these services with ``--profile crm``.
5. Verify signup and recovery from broker/CRM outages in staging.

``CRM_ENABLED = False`` pauses synchronization. Signups while disabled require
an explicit backfill.

Matching and operations
-----------------------

People are matched by source user ID, explicit mapping, then confirmed email.
Existing contact details and employers are preserved. Companies reuse an explicit
mapping or the existing account's company; otherwise a name or domain match
requires manual reconciliation. Ambiguous matches and conflicting source IDs
remain pending. Retries reuse deterministic record IDs.

Resynchronize a supporter or supply a mapping::

    python manage.py crm-sync 123
    python manage.py crm-sync 123 --company-id <crm-company-uuid>
    python manage.py crm-sync 123 --person-id <crm-person-uuid>

Inspect ``crm_sync`` fields ``pending``, ``attempts``, ``last_error``,
``next_attempt_at`` and ``synced_at`` for status. Matching, schema and authentication
errors require operator action. Deleted or detached users require manual review;
CRM deletion is not automated.
