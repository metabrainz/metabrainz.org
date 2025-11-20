import React, { JSX } from "react";
import { createRoot } from "react-dom/client";
import { getPageProps } from "./utils";
import { OAuthScopeDesc } from "./forms/utils";
import ProfileTabs from "./ProfileTabs";
import ApplicationRow from "./ApplicationRow";

type ApplicationProps = {
  applications: Array<{
    name: string;
    website: string;
    client_id: string;
    client_secret: string;
  }>;
  tokens: Array<{
    name: string;
    website: string;
    scopes: Array<Scope>;
    client_id: string;
  }>;
};

function Applications({ applications, tokens }: ApplicationProps): JSX.Element {
  return (
    <>
      <ProfileTabs activeTab="applications" />

      <div>
        <h3>
          Your applications
          <a
            href="/profile/applications/create"
            className="btn btn-success pull-right"
          >
            <span className="glyphicon glyphicon-plus-sign" />
            Create new application
          </a>
        </h3>
      </div>

      {applications.length === 0 ? (
        <p className="lead" style={{ textAlign: "center" }}>
          No applications found
        </p>
      ) : (
        <table className="oauth-applications-table table table-hover">
          <thead>
            <tr>
              <th>Name</th>
              <th>Website</th>
              <th>Client ID</th>
              <th style={{ width: "400px" }}>Client secret</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {applications.map((application) => (
              <ApplicationRow
                key={application.client_id}
                application={application}
              />
            ))}
          </tbody>
        </table>
      )}
      <hr />

      <h3>Authorized applications</h3>
      {tokens.length === 0 ? (
        <p className="lead" style={{ textAlign: "center" }}>
          No tokens found
        </p>
      ) : (
        <table className="oauth-applications-table table table-hover">
          <thead>
            <tr>
              <th>Name</th>
              <th>Website</th>
              <th>Access</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {tokens.map((token) => (
              <tr>
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
                      Revoke access
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

  const renderRoot = createRoot(domContainer!);
  renderRoot.render(
    <Applications applications={applications} tokens={tokens} />
  );
});
