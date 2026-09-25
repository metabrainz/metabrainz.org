from datetime import datetime, timezone
from decimal import Decimal
import json
from urllib.parse import urlparse

from metabrainz.crm.client import CrmMatchRequired


def sync_supporter(client, supporter, mapping):
    user = supporter.user
    if user is None or user.deleted:
        raise CrmMatchRequired("Supporter has no current user; review the CRM record manually")

    person = client.find("people", "metabrainzUserId", user.id)
    if mapping.person_id:
        mapped = client.mapped("people", str(mapping.person_id))
        if person and person["id"] != mapped["id"]:
            raise CrmMatchRequired("Person mapping conflicts with source identity")
        person = mapped
    if person is None and user.email:
        person = client.find("people", "emails.primaryEmail", user.email)
    person_id = person["id"] if person else client.record_id("user", user.id)
    if person is None:
        person = client.find("people", "id", person_id)
    if person and person.get("metabrainzUserId") not in (None, "", str(user.id)):
        raise CrmMatchRequired("Person belongs to a different MetaBrainz user")
    person_data = {
        "metabrainzUserId": str(user.id),
        "metabrainzUsername": user.name,
        "metabrainzEmailVerified": user.email is not None,
    }
    # Preserve existing contact details; source email is kept separately.
    person_data["metabrainzEmail"] = user.get_email_any() or ""
    if person is None:
        person_data.update({
            "name": {"firstName": supporter.contact_name, "lastName": ""},
            "emails": {"primaryEmail": user.get_email_any() or "", "additionalEmails": []},
        })
    client.save("people", "Person", person_id, person_data, exists=person is not None)

    account = client.find("supporterAccounts", "metabrainzSupporterId", supporter.id)
    company_id = None
    if mapping.company_id:
        company_id = client.mapped("companies", str(mapping.company_id))["id"]
    elif account and account.get("companyId"):
        company_id = client.mapped("companies", account["companyId"])["id"]
    elif supporter.org_name:
        company_id = client.record_id("supporter-company", supporter.id)
        company = client.find("companies", "id", company_id)
        if company is None:
            # Never silently merge organizations on a name or domain supplied at signup.
            candidates = client.find("companies", "name", supporter.org_name)
            if candidates:
                raise CrmMatchRequired("Existing company name matches; set an explicit company mapping")
            website = (supporter.website_url or "").strip()
            domain = (urlparse(website if "://" in website else "//" + website).hostname or "").rstrip(".")
            if domain and client.find("companies", "domainName.primaryLinkUrl", domain):
                raise CrmMatchRequired("Existing company domain matches; set an explicit company mapping")
            client.save("companies", "Company", company_id, {
                "name": supporter.org_name,
                "domainName": {"primaryLinkUrl": domain},
            })

    # Do not overwrite an existing person's employer. The account can still link both.
    if company_id and (person is None or not person.get("companyId")):
        client.save("people", "Person", person_id, {"companyId": company_id}, exists=True)

    account_id = account["id"] if account else client.record_id("supporter", supporter.id)
    if account is None:
        account = client.find("supporterAccounts", "id", account_id)
    client.save("supporterAccounts", "SupporterAccount", account_id, {
        "name": supporter.org_name or supporter.contact_name,
        "metabrainzSupporterId": str(supporter.id),
        "primaryContactId": person_id, "companyId": company_id,
        "contactName": supporter.contact_name,
        "isCommercial": supporter.is_commercial, "state": supporter.state.upper(),
        "tierId": str(supporter.tier_id) if supporter.tier_id is not None else "",
        "tierName": supporter.tier.name if supporter.tier else "",
        "amountPledged": {
            "amountMicros": int(supporter.amount_pledged * Decimal(1000000))
            if supporter.amount_pledged is not None else None,
            "currencyCode": "USD",
        },
        "goodStanding": supporter.good_standing,
        "dataUsageDescription": supporter.data_usage_desc or "",
        "datasets": json.dumps([
            {"id": d.id, "name": d.name} for d in sorted(supporter.datasets, key=lambda d: d.id)
        ]),
        "sourceCreatedAt": supporter.created.isoformat() if supporter.created else None,
        "lastSyncedAt": datetime.now(timezone.utc).isoformat(),
    }, exists=account is not None)
    return person_id, company_id
