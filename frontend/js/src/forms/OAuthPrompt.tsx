import React, { JSX } from "react";
import { createRoot } from "react-dom/client";
import { getPageProps } from "../utils";
import { OAuthScopeDesc } from "./utils";

type OAuthPromptProps = {
  scopes: Array<Scope>;
  csrf_token: string;
  client_name: string;
  cancel_url: string;
  submission_url: string;
};

function OAuthPrompt({
  scopes,
  csrf_token,
  cancel_url,
  submission_url,
  client_name,
}: OAuthPromptProps): JSX.Element {
  return (
    <div id="oauth-prompt">
      <h1 className="page-title">{client_name}</h1>
      <p style={{ fontSize: "1.1em" }}>
        This app requested permission to access:
      </p>
      <div className="permissions">
        <div className="permission">
          <div className="icon">
            <img src="/static/img/oauth/identity.svg" alt="Identity" />
          </div>
          <div className="description">Your identity on MetaBrainz</div>
        </div>

        <div className="permission">{OAuthScopeDesc(scopes)}</div>
      </div>
      <form method="POST" action={submission_url} className="form-horizontal">
        <div className="form-group">
          <div className="col-sm-offset-4 col-sm-5">
            <input
              id="csrf_token"
              name="csrf_token"
              type="hidden"
              value={csrf_token}
            />
            <input id="confirm" name="confirm" type="hidden" value="yes" />
          </div>
        </div>
        <div className="form-group">
          <div className="col-md-offset-3 col-md-1">
            <a href={cancel_url} className="btn btn-default">
              Cancel
            </a>
          </div>
          <div className="col-md-1" style={{ marginLeft: "8px" }}>
            <button type="submit" className="btn btn-primary">
              Allow access
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}

document.addEventListener("DOMContentLoaded", () => {
  const { domContainer, reactProps } = getPageProps();
  const { csrf_token, scopes, client_name, cancel_url, submission_url } =
    reactProps;

  const renderRoot = createRoot(domContainer!);
  renderRoot.render(
    <OAuthPrompt
      scopes={scopes}
      csrf_token={csrf_token}
      client_name={client_name}
      cancel_url={cancel_url}
      submission_url={submission_url}
    />
  );
});
