import React, { JSX } from "react";
import { useTranslation } from "react-i18next";
import { getPageProps, renderRoot } from "./utils";
import { OAuthScopeDesc } from "./forms/utils";
import ProfileTabs from "./ProfileTabs";
import ApplicationRow from "./ApplicationRow";

type ApplicationProps = {
  applications: Array<{
    name: string;
    website: string;
    client_id: string;
    client_secret: string;
    privileges?: Array<string>;
  }>;
  tokens: Array<{
    name: string;
    website: string;
    scopes: Array<Scope>;
    client_id: string;
  }>;
};

function Applications({ applications, tokens }: ApplicationProps): JSX.Element {
  const { t } = useTranslation();

  const showPrivileges = applications.some(
    (application) => (application.privileges?.length ?? 0) > 0
  );

  return (
    <>
      <ProfileTabs activeTab="applications" />

      <div>
        <h3>
          {t("Your applications")}
          <a
            href="/profile/applications/create"
            className="btn btn-success pull-right"
          >
            <span className="glyphicon glyphicon-plus-sign" />
            {" "}{t("Create new application")}
          </a>
        </h3>
      </div>

      {applications.length === 0 ? (
        <p className="lead" style={{ textAlign: "center" }}>
          {t("No applications found")}
        </p>
      ) : (
        <table className="oauth-applications-table table table-hover">
          <thead>
            <tr>
              <th>{t("Name")}</th>
              <th>{t("Website")}</th>
              <th>{t("Client ID")}</th>
              <th style={{ width: "400px" }}>{t("Client secret")}</th>
              {showPrivileges && <th>{t("Privileges")}</th>}
              <th>{t("Actions")}</th>
            </tr>
          </thead>
          <tbody>
            {applications.map((application) => (
              <ApplicationRow
                key={application.client_id}
                application={application}
                showPrivileges={showPrivileges}
              />
            ))}
          </tbody>
        </table>
      )}
      <hr />

      <h3>{t("Authorized applications")}</h3>
      {tokens.length === 0 ? (
        <p className="lead" style={{ textAlign: "center" }}>
          {t("No tokens found")}
        </p>
      ) : (
        <table className="oauth-applications-table table table-hover">
          <thead>
            <tr>
              <th>{t("Name")}</th>
              <th>{t("Website")}</th>
              <th>{t("Access")}</th>
              <th>{t("Actions")}</th>
            </tr>
          </thead>
          <tbody>
            {tokens.map((token) => (
              <tr key={token.client_id}>
                <td>
                  <b>{token.name}</b>
                </td>
                <td>{token.website}</td>
                <td>{OAuthScopeDesc(token.scopes)}</td>
                <td>
                  <form
                    action={`/profile/application/revoke/${token.client_id}/user`}
                    method="post"
                    className="btn btn-danger btn-xs"
                  >
                    <button
                      type="submit"
                      className="btn btn-danger"
                      style={{ color: "white" }}
                    >
                      {t("Revoke access")}
                    </button>
                  </form>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  );
}

document.addEventListener("DOMContentLoaded", () => {
  const { domContainer, reactProps } = getPageProps();
  const { applications, tokens } = reactProps;

  renderRoot(
    domContainer!,
    <Applications applications={applications} tokens={tokens} />
  );
});
