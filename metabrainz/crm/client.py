from uuid import NAMESPACE_URL, uuid5

import requests


class CrmError(Exception):
    """A safe-to-log error, without response bodies or credentials."""


class CrmMatchRequired(CrmError):
    pass


class TwentyClient:
    def __init__(self, config):
        self.base_url = config.get("CRM_URL", "").rstrip("/")
        self.source = config.get("CRM_SOURCE", "metabrainz.org")
        self.timeout = config.get("CRM_HTTP_TIMEOUT", 10)
        token = config.get("CRM_API_KEY")
        if not self.base_url.startswith("https://") or not token:
            raise CrmError("CRM_URL must use HTTPS and CRM_API_KEY must be configured")
        self.session = requests.Session()
        self.session.headers["Authorization"] = f"Bearer {token}"

    def close(self):
        self.session.close()

    def request(self, method, path, **kwargs):
        try:
            response = self.session.request(
                method, f"{self.base_url}/{path}", timeout=self.timeout,
                allow_redirects=False, **kwargs,
            )
        except requests.RequestException:
            raise CrmError("Twenty connection failed") from None
        if not 200 <= response.status_code < 300:
            raise CrmError(f"Twenty returned HTTP {response.status_code}")
        try:
            body = response.json()
            if body.get("errors") or not isinstance(body.get("data"), dict):
                raise ValueError()
            return body
        except (ValueError, AttributeError):
            raise CrmError("Invalid Twenty response") from None

    def find(self, plural, field, value):
        singular, fields = {
            "people": ("Person", "id metabrainzUserId companyId"),
            "companies": ("Company", "id"),
            "supporterAccounts": ("SupporterAccount", "id metabrainzSupporterId companyId"),
        }[plural]
        condition = {"eq": str(value)}
        for part in reversed(field.split(".")):
            condition = {part: condition}
        body = self.request("POST", "graphql", json={
            "query": f"""query FindRecord($filter: {singular}FilterInput!) {{
                {plural}(filter: $filter, first: 2) {{
                    edges {{ node {{ {fields} }} }}
                    pageInfo {{ hasNextPage }}
                }}
            }}""",
            "variables": {"filter": condition},
        })
        try:
            connection = body["data"][plural]
            records = [edge["node"] for edge in connection["edges"]]
            has_next = connection["pageInfo"]["hasNextPage"]
            if any(not isinstance(record, dict) or not record.get("id") for record in records):
                raise ValueError()
        except (KeyError, TypeError, ValueError):
            raise CrmError("Invalid Twenty record list") from None
        if len(records) > 1 or has_next:
            raise CrmMatchRequired(f"Multiple {plural} match; explicit reconciliation required")
        return records[0] if records else None

    def mapped(self, plural, record_id):
        record = self.find(plural, "id", record_id)
        if record is None:
            raise CrmMatchRequired(f"Mapped {plural} record is missing")
        return record

    def save(self, plural, singular, record_id, data, exists=False):
        body = self.request(
            "PATCH" if exists else "POST",
            f"rest/{plural}/{record_id}" if exists else f"rest/{plural}",
            json=data if exists else {"id": record_id, **data},
        )
        record = body["data"].get(("update" if exists else "create") + singular)
        if not isinstance(record, dict) or record.get("id") != record_id:
            raise CrmError("Invalid Twenty write response")
        return record

    def record_id(self, kind, source_id):
        return str(uuid5(NAMESPACE_URL, f"https://{self.source}/crm/{kind}/{source_id}"))
