from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import requests

from metabrainz.crm.client import CrmError, CrmMatchRequired, TwentyClient
from metabrainz.crm.sync import sync_supporter


@pytest.fixture
def client():
    client = TwentyClient({"CRM_URL": "https://crm.example", "CRM_API_KEY": "secret"})
    yield client
    client.close()


def test_api_contract(client, requests_mock):
    get = requests_mock.post("https://crm.example/graphql", json={
        "data": {"people": {"edges": [], "pageInfo": {"hasNextPage": False}}},
    })
    assert client.find("people", "metabrainzUserId", 42) is None
    assert get.last_request.json()["variables"] == {"filter": {"metabrainzUserId": {"eq": "42"}}}
    assert get.last_request.headers["Authorization"] == "Bearer secret"
    record_id = client.record_id("user", 42)
    requests_mock.post("https://crm.example/rest/people", json={"data": {"createPerson": {"id": record_id}}})
    assert client.save("people", "Person", record_id, {"metabrainzUserId": "42"})["id"] == record_id
    requests_mock.patch(f"https://crm.example/rest/people/{record_id}", json={
        "data": {"updatePerson": {"id": record_id}},
    })
    client.save("people", "Person", record_id, {"metabrainzUsername": "test"}, exists=True)


def test_ambiguous_and_truncated_matches_fail(client, requests_mock):
    requests_mock.post("https://crm.example/graphql", json={
        "data": {"people": {"edges": [{"node": {"id": "one"}}], "pageInfo": {"hasNextPage": True}}},
    })
    with pytest.raises(CrmMatchRequired):
        client.find("people", "metabrainzUserId", 42)


def test_company_name_is_a_graphql_variable(client, requests_mock):
    request = requests_mock.post("https://crm.example/graphql", json={
        "data": {"companies": {"edges": [], "pageInfo": {"hasNextPage": False}}},
    })
    name = 'Société "Music", Inc. (Europe)'
    assert client.find("companies", "name", name) is None
    body = request.last_request.json()
    assert body["variables"] == {"filter": {"name": {"eq": name}}}
    assert name not in body["query"]


def test_graphql_errors_are_not_treated_as_missing_records(client, requests_mock):
    requests_mock.post("https://crm.example/graphql", json={
        "data": None, "errors": [{"message": "sensitive server details"}],
    })
    with pytest.raises(CrmError, match="Invalid Twenty response"):
        client.find("people", "metabrainzUserId", 42)


@pytest.mark.parametrize("status", [301, 400, 401, 429, 500])
def test_http_errors_do_not_expose_body(client, requests_mock, status):
    requests_mock.post("https://crm.example/graphql", status_code=status, text="secret personal data")
    with pytest.raises(CrmError, match=f"HTTP {status}") as error:
        client.find("people", "id", "test")
    assert "secret" not in str(error.value)


def test_timeout_is_safe(client, requests_mock):
    requests_mock.post("https://crm.example/graphql", exc=requests.Timeout("secret"))
    with pytest.raises(CrmError, match="connection failed"):
        client.find("people", "id", "test")


@pytest.fixture
def supporter():
    return SimpleNamespace(
        id=42, user=SimpleNamespace(id=17, deleted=False, email="person@example.com", name="username",
                                    get_email_any=lambda: "person@example.com"),
        contact_name="Full Unsplit Name", org_name=None, website_url=None,
        is_commercial=False, state="active", tier_id=None, tier=None,
        amount_pledged=Decimal("12.34"), good_standing=False, data_usage_desc="Research",
        datasets=[SimpleNamespace(id=2, name="MusicBrainz")], created=datetime.now(timezone.utc),
    )


def memory_client(client):
    records = {"people": {}, "companies": {}, "supporterAccounts": {}}

    def find(plural, field, value):
        for record in records[plural].values():
            actual = record
            for key in field.split("."):
                actual = actual.get(key) if isinstance(actual, dict) else None
            if actual == str(value):
                return dict(record)
        return None

    def save(plural, singular, record_id, data, exists=False):
        if not exists:
            assert record_id not in records[plural], "Duplicate create"
        records[plural].setdefault(record_id, {"id": record_id}).update(data)
        return records[plural][record_id]

    client.find = Mock(side_effect=find)
    client.save = Mock(side_effect=save)
    return records


def test_individual_and_duplicate_delivery(client, supporter):
    records = memory_client(client)
    mapping = SimpleNamespace(person_id=None, company_id=None)
    sync_supporter(client, supporter, mapping)
    sync_supporter(client, supporter, mapping)
    assert len(records["people"]) == len(records["supporterAccounts"]) == 1
    assert records["companies"] == {}
    account = next(iter(records["supporterAccounts"].values()))
    assert account["amountPledged"]["amountMicros"] == 12340000
    assert account["state"] == "ACTIVE"
    assert account["contactName"] == "Full Unsplit Name"


def test_partial_success_retry_and_company_link(client, supporter):
    records = memory_client(client)
    supporter.org_name = "New Company"
    supporter.is_commercial = True
    supporter.state = "pending"
    mapping = SimpleNamespace(person_id=None, company_id=None)
    save = client.save.side_effect

    def lost_response(plural, *args, **kwargs):
        result = save(plural, *args, **kwargs)
        if plural == "companies":
            raise CrmError("Twenty connection failed")
        return result

    client.save.side_effect = lost_response
    with pytest.raises(CrmError):
        sync_supporter(client, supporter, mapping)
    client.save.side_effect = save
    sync_supporter(client, supporter, mapping)
    assert all(len(rows) == 1 for rows in records.values())
    account = next(iter(records["supporterAccounts"].values()))
    assert account["companyId"] == next(iter(records["companies"]))
    assert account["state"] == "PENDING"


def test_preserve_existing_contact_and_employer(client, supporter):
    records = memory_client(client)
    person_id = client.record_id("existing", 1)
    records["people"][person_id] = {
        "id": person_id, "emails": {"primaryEmail": supporter.user.email},
        "name": {"firstName": "CRM name", "lastName": ""}, "companyId": "original-company",
    }
    mapping = SimpleNamespace(person_id=None, company_id=None)
    sync_supporter(client, supporter, mapping)
    person = records["people"][person_id]
    assert person["name"]["firstName"] == "CRM name"
    assert person["companyId"] == "original-company"
    assert person["metabrainzUserId"] == "17"


def test_unverified_email_not_matched(client, supporter):
    memory_client(client)
    supporter.user.email = None
    sync_supporter(client, supporter, SimpleNamespace(person_id=None, company_id=None))
    assert all(call.args[1] != "emails.primaryEmail" for call in client.find.call_args_list)


def test_conflicting_source_user_is_rejected(client, supporter):
    records = memory_client(client)
    records["people"]["existing"] = {
        "id": "existing", "emails": {"primaryEmail": supporter.user.email}, "metabrainzUserId": "99",
    }
    with pytest.raises(CrmMatchRequired):
        sync_supporter(client, supporter, SimpleNamespace(person_id=None, company_id=None))
    client.save.assert_not_called()


def test_existing_company_requires_mapping(client, supporter):
    records = memory_client(client)
    supporter.org_name = "Existing Company"
    company_id = client.record_id("existing-company", 1)
    records["companies"][company_id] = {"id": company_id, "name": supporter.org_name}
    mapping = SimpleNamespace(person_id=None, company_id=None)
    with pytest.raises(CrmMatchRequired):
        sync_supporter(client, supporter, mapping)
    mapping.company_id = company_id
    sync_supporter(client, supporter, mapping)
    assert len(records["companies"]) == 1
    assert next(iter(records["supporterAccounts"].values()))["companyId"] == company_id


@pytest.mark.parametrize("website", [None, "", "https://Example.COM/about", "example.com"])
def test_company_create_uses_standard_fields(client, supporter, website):
    records = memory_client(client)
    supporter.org_name = "New Company"
    supporter.website_url = website
    sync_supporter(client, supporter, SimpleNamespace(person_id=None, company_id=None))
    company_id = client.record_id("supporter-company", supporter.id)
    assert records["companies"][company_id] == {
        "id": company_id,
        "name": "New Company",
        "domainName": {"primaryLinkUrl": "example.com" if website else ""},
    }


@pytest.mark.parametrize("website", [
    "https://example.com", "http://EXAMPLE.com/", "example.com/about",
    "https://example.com:443/path?query=1", "https://example.com./",
])
def test_created_company_domain_requires_mapping(client, supporter, website):
    records = memory_client(client)
    supporter.org_name = "First Company"
    supporter.website_url = "https://example.com"
    mapping = SimpleNamespace(person_id=None, company_id=None)
    sync_supporter(client, supporter, mapping)
    company_id = next(iter(records["companies"]))

    supporter.id += 1
    supporter.org_name = "Different Company Name"
    supporter.website_url = website
    with pytest.raises(CrmMatchRequired, match="Existing company domain matches"):
        sync_supporter(client, supporter, mapping)
    assert len(records["companies"]) == len(records["supporterAccounts"]) == 1

    mapping.company_id = company_id
    sync_supporter(client, supporter, mapping)
    assert len(records["companies"]) == 1
    assert len(records["supporterAccounts"]) == 2
