import React, { JSX } from "react";
import { createRoot } from "react-dom/client";
import { getPageProps } from "./utils";
import { OAuthScopeDesc } from "./forms/utils";

type ApplicationProps = {
  urlPrefix: string;
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

function Applications({
  applications,
  tokens,
  urlPrefix,
}: ApplicationProps): JSX.Element {
  return (
    <>
      <h2>Applications</h2>

      <div className="clearfix">
        <h3 className="pull-left">Your applications</h3>
        <a
          href={`${urlPrefix}/client/create`}
          className="btn btn-success pull-right"
          style={{ marginTop: "12px" }}
        >
          <span className="glyphicon glyphicon-plus-sign" />
          Create new application
        </a>
      </div>
      {applications.length === 0 ? (
        <p className="lead" style={{ textAlign: "center" }}>
          No applications found
        </p>
      ) : (
        <table className="table table-hover">
          <thead>
            <tr>
              <th>Name</th>
              <th>Website</th>
              <th>Client ID</th>
              <th>Client secret</th>
              {/* eslint-disable-next-line jsx-a11y/control-has-associated-label */}
              <th />
              {/* eslint-disable-next-line jsx-a11y/control-has-associated-label */}
              <th />
            </tr>
          </thead>
          <tbody>
            {applications.map((application) => (
              <tr>
                <td>{application.name}</td>
                <td>{application.website}</td>
                <td>{application.client_id}</td>
                <td>{application.client_secret}</td>
                <td>
                  <a
                    className="btn btn-primary btn-xs"
                    href={`${urlPrefix}/client/edit/${application.client_id}`}
                  >
                    Modify
                  </a>
                </td>
                <td>
                  <a
                    className="btn btn-danger btn-xs"
                    href={`${urlPrefix}/client/delete/${application.client_id}`}
                  >
                    Delete
                  </a>
                </td>
              </tr>
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
        <table className="table table-hover">
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
                    action={`${urlPrefix}/client/${token.client_id}/revoke/user`}
                    method="post"
                    className="btn btn-danger btn-xs"
                  >
                    <button
                      type="submit"
                      className="btn-link"
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
  const { domContainer, reactProps, globalProps } = getPageProps();
  const { applications, tokens } = reactProps;
  const { url_prefix } = globalProps;

  const renderRoot = createRoot(domContainer!);
  renderRoot.render(
    <Applications
      applications={applications}
      tokens={tokens}
      urlPrefix={url_prefix}
    />
  );
});
