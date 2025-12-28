import React, { JSX, useCallback, useState } from "react";
import { createRoot } from "react-dom/client";
import { getPageProps } from "./utils";
import ProfileTabs from "./ProfileTabs";

type ProfileProps = {
  user: User;
  csrf_token?: string;
};

type EmailDisplayProps = {
  email: string | null;
  unconfirmed_email: string | null;
  csrf_token?: string;
};

function EmailDisplay({
  email,
  unconfirmed_email,
  csrf_token,
}: EmailDisplayProps): JSX.Element {
  const hasBothEmails = email && unconfirmed_email;

  const ResendButton = () => (
    <form
      method="post"
      action="/resend-verification-email"
      style={{ display: "inline-block" }}
    >
      <input
        id="csrf_token"
        name="csrf_token"
        type="hidden"
        value={csrf_token}
      />
      <button className="btn btn-link text-danger" type="submit" style={{ padding: "0 4px" }}>
        (Resend Verification Email)
      </button>
    </form>
  );

  return (
    <>
      {hasBothEmails ? (
        <>
          <strong>Current: </strong>
          {email}{" "}
          <span className="badge" style={{ background: "green" }}>
            Verified
          </span>
          <br />
          <strong>New: </strong>
          {unconfirmed_email}{" "}
          <span className="badge" style={{ background: "red" }}>
            Unverified
          </span>
          <ResendButton />
          <br />
          <small className="text-muted">
            Your current email will be replaced once the new email is verified.
          </small>
        </>
      ) : email ? (
        <>
          <>{email}{" "}</>
          <span className="badge" style={{ background: "green" }}>
            Verified
          </span>
        </>
      ) : unconfirmed_email ? (
        <>
          <>{unconfirmed_email}{" "}</>
          <span className="badge" style={{ background: "red" }}>
            Unverified
          </span>
          <ResendButton />
        </>
      ) : null}
    </>
  );
}

function SupporterProfile({ user, csrf_token }: ProfileProps) {
  const { email, unconfirmed_email, supporter } = user;
  const {
    is_commercial,
    tier,
    state,
    contact_name,
    org_name,
    website_url,
    api_url,
    datasets,
    good_standing,
    token,
  } = supporter!;
  const [currentToken, setCurrentToken] = useState(token);

  const regenerateToken = useCallback(async () => {
    if (
      !currentToken ||
      window.confirm(
        "Are you sure you want to generate new access token? Current token will be revoked!"
      )
    ) {
      const response = await fetch("/supporters/profile/regenerate-token", {
        method: "POST",
      });
      if (!response.ok) {
        window.alert("Failed to generate new access token!");
      } else {
        const data = await response.json();
        setCurrentToken(data.token);
      }
    }
  }, [currentToken]);

  let applicationState;
  if (state === "rejected") {
    applicationState = (
      <>
        <p>
          <b>
            Your application for using the Live Data Feed has been rejected.
          </b>
        </p>
        <p>
          You do not have permission to use our data in a public commercial
          product.
        </p>
      </>
    );
  } else if (state === "pending") {
    applicationState = (
      <>
        <p>
          <b>Your application for using the Live Data Feed is still pending.</b>
        </p>
        <p>
          You may use our data and APIs for evaluation/development purposes
          while your application is pending.
        </p>
      </>
    );
  } else if (state === "waiting") {
    applicationState = (
      <>
        <p>
          <b>
            Your application for using the Live Data Feed is waiting to finalize
            our support agreement.
          </b>
        </p>
        <p>
          You may use our data and APIs for evaluation and development purposes,
          but you may not use the data in a public commercial product. Once you
          are nearing the public release of a product that contains our data,
          please
          <a href="/contact">contact us</a> again to finalize our support
          agreement.
        </p>
      </>
    );
  } else if (!good_standing) {
    applicationState = (
      <>
        <p>
          <b>Your use of the Live Data Feed is pending suspension.</b>
        </p>
        <p>
          Your account is in bad standing, which means that you are more than 60
          days behind in support payments. If you think this is a mistake,
          please <a href="/contact">contact us</a>.
        </p>
      </>
    );
  } else {
    applicationState = <p>Unknown. :(</p>;
  }

  let stateClass;
  if (state === "active") {
    stateClass = "text-success";
  } else if (state === "rejected") {
    stateClass = "text-danger";
  } else if (state === "pending") {
    stateClass = "text-primary";
  } else {
    stateClass = "text-warning";
  }

  return (
    <>
      <div className="row" style={{ marginBottom: "1.5rem" }}>
        <div className="col-md-12">
          <div className="well" style={{ marginBottom: 0 }}>
            <div className="row">
              <div className="col-sm-4">
                <strong>Type:</strong>{" "}
                {is_commercial ? "Commercial" : "Non-commercial"}
              </div>
              {is_commercial && (
                <div className="col-sm-4">
                  <strong>Tier:</strong> {tier.name}
                </div>
              )}
              <div className="col-sm-4">
                <strong>State:</strong>
                <span className={stateClass}> {state.toUpperCase()}</span>
              </div>
            </div>
          </div>
          {!is_commercial && (
            <p className="text-muted" style={{ marginTop: "0.5rem" }}>
              If you would like to change your account from non-commercial to
              commercial, please <a href="/contact">contact us</a>.
            </p>
          )}
        </div>
      </div>

      <div className="row" style={{ marginBottom: "1.5rem", display: "flex", flexWrap: "wrap" }}>
        {is_commercial && (
          <div className="col-md-6" style={{ display: "flex" }}>
            <div className="panel panel-default" style={{ flex: 1 }}>
              <div className="panel-heading">
                <h3 className="panel-title">Organization Information</h3>
              </div>
              <div className="panel-body">
                <dl style={{ marginBottom: 0 }}>
                  <dt>Name</dt>
                  <dd style={{ marginBottom: "1rem" }}>
                    {org_name || <em className="text-muted">Unspecified</em>}
                  </dd>
                  <dt>Website URL</dt>
                  <dd style={{ marginBottom: "1rem" }}>
                    {website_url || <em className="text-muted">Unspecified</em>}
                  </dd>
                  <dt>API URL</dt>
                  <dd>
                    {api_url || <em className="text-muted">Unspecified</em>}
                  </dd>
                </dl>
                <p className="text-muted" style={{ marginTop: "1rem", marginBottom: 0 }}>
                  <a href="/contact">Contact us</a> to update this information.
                </p>
              </div>
            </div>
          </div>
        )}
        <div className={is_commercial ? "col-md-6" : "col-md-12"} style={{ display: "flex" }}>
          <div className="panel panel-default" style={{ flex: 1 }}>
            <div className="panel-heading">
              <h3 className="panel-title">Contact Information</h3>
            </div>
            <div className="panel-body">
              <dl style={{ marginBottom: 0 }}>
                <dt>Contact Name</dt>
                <dd style={{ marginBottom: "1rem" }}>{contact_name}</dd>
                <dt>Contact Email</dt>
                <dd style={{ marginBottom: !is_commercial ? "1rem" : 0 }}>
                  <EmailDisplay
                    email={email}
                    unconfirmed_email={unconfirmed_email}
                    csrf_token={csrf_token}
                  />
                </dd>
                {!is_commercial && (
                  <>
                    <dt>Datasets Used</dt>
                    <dd>{datasets.map((d) => d.name).join(", ")}</dd>
                  </>
                )}
              </dl>
              <a
                href="/profile/edit"
                className="btn btn-warning"
                style={{ marginTop: "1rem" }}
              >
                {is_commercial
                  ? "Edit Contact Information"
                  : "Edit Datasets / Contact Information"}
              </a>
            </div>
          </div>
        </div>
      </div>

      {is_commercial && (
        <div className="row" style={{ marginBottom: "1.5rem" }}>
          <div className="col-md-12">
            {(state === "active" || state === "limited") && good_standing ? (
              <div className="panel panel-success">
                <div className="panel-heading">
                  <h3 className="panel-title">Data Use Permission Granted</h3>
                </div>
                <div className="panel-body">
                  <p>
                    <b>Your support agreement has been completed -- thank you!</b>
                  </p>
                  <p>
                    You have permission to use any of the data published by the
                    MetaBrainz Foundation. This includes data dumps released under a
                    Creative Commons non-commercial license.
                  </p>
                  <ul className="text-muted">
                    <li>
                      If your support falls behind by more than 60 days, this
                      permission may be withdrawn.
                    </li>
                    <li>
                      IP addresses from which replication packets are downloaded are
                      logged.
                    </li>
                  </ul>
                </div>
              </div>
            ) : (
              <div className="panel panel-warning">
                <div className="panel-heading">
                  <h3 className="panel-title">Limited/No Data Use Permission</h3>
                </div>
                <div className="panel-body">{applicationState}</div>
              </div>
            )}
          </div>
        </div>
      )}

      {(state === "active" || state === "limited") && good_standing && (
        <div className="row" style={{ marginBottom: "1.5rem" }}>
          <div className="col-md-12">
            <div className="panel panel-primary">
              <div className="panel-heading">
                <h3 className="panel-title">Data Download</h3>
              </div>
              <div className="panel-body">
                {!is_commercial && (
                  <p>
                    Thank you for registering with us -- we really appreciate it!
                  </p>
                )}
                <p>Proceed to our download page to download datasets:</p>
                <a href="/download" className="btn btn-primary">
                  Download Datasets
                </a>
              </div>
            </div>
          </div>
        </div>
      )}

      {state === "active" && (
        <div className="row" style={{ marginBottom: "1.5rem" }}>
          <div className="col-md-12">
            <div className="panel panel-default">
              <div className="panel-heading">
                <h3 className="panel-title">Live Data Feed Access Token</h3>
              </div>
              <div className="panel-body">
                <p className="text-muted" style={{ fontStyle: "italic" }}>
                  This access token should be considered private. Don&apos;t check
                  it into publicly visible version control systems. If exposed,
                  generate a new one immediately.
                </p>
                <div
                  className="well"
                  style={{
                    fontFamily: "monospace",
                    fontSize: "14pt",
                    color: "#AA0000",
                    wordBreak: "break-all",
                    marginBottom: "1rem",
                  }}
                >
                  {currentToken || "[ no valid token currently ]"}
                </div>
                <button
                  className="btn btn-default"
                  type="button"
                  onClick={regenerateToken}
                >
                  Generate New Token
                </button>
                <p style={{ marginTop: "1rem", marginBottom: 0 }}>
                  See the <a href="/api">API documentation</a> for more information.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

function UserProfile({ user, csrf_token }: ProfileProps): JSX.Element {
  const { name, email, unconfirmed_email } = user;
  return (
    <>
      <div className="row" style={{ marginBottom: "1.5rem" }}>
        <div className="col-md-12">
          <div className="panel panel-default">
            <div className="panel-heading">
              <h3 className="panel-title">Contact Information</h3>
            </div>
            <div className="panel-body">
              <dl style={{ marginBottom: 0 }}>
                <dt>Name</dt>
                <dd style={{ marginBottom: "1rem" }}>{name}</dd>
                <dt>Email</dt>
                <dd>
                  <EmailDisplay
                    email={email}
                    unconfirmed_email={unconfirmed_email}
                    csrf_token={csrf_token}
                  />
                </dd>
              </dl>
              <a
                href="/profile/edit"
                className="btn btn-warning"
                style={{ marginTop: "1rem" }}
              >
                Edit Information
              </a>
            </div>
          </div>
        </div>
      </div>

      <div className="row" style={{ marginBottom: "1.5rem" }}>
        <div className="col-md-12">
          <div className="panel panel-info">
            <div className="panel-heading">
              <h3 className="panel-title">Want access to MetaBrainz datasets?</h3>
            </div>
            <div className="panel-body">
              <p>
                Upgrade your account to a supporter account to access our datasets and
                the Live Data Feed. Choose between non-commercial (free) and
                commercial options.
              </p>
              <a href="/supporters/account-type" className="btn btn-primary">
                Become a Supporter
              </a>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

function DeleteAccountSection() {
  return (
    <div className="row" style={{ marginBottom: "1.5rem" }}>
      <div className="col-md-12">
        <div className="panel panel-danger">
          <div className="panel-heading">
            <h3 className="panel-title">Danger Zone</h3>
          </div>
          <div className="panel-body">
            <p>
              <strong>Delete your account</strong>
            </p>
            <p className="text-muted">
              Once you delete your account, there is no going back. Please be
              certain.
            </p>
            <a href="/profile/delete" className="btn btn-danger">
              Delete My Account
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}

function SupporterAccountDeletionNotice() {
  return (
    <div className="row" style={{ marginBottom: "1.5rem" }}>
      <div className="col-md-12">
        <div className="panel panel-default">
          <div className="panel-heading">
            <h3 className="panel-title">Account Deletion</h3>
          </div>
          <div className="panel-body">
            <p>
              <strong>Need to delete your account?</strong>
            </p>
            <p className="text-muted" style={{ marginBottom: 0 }}>
              Deletion of supporter accounts requires manual review. Please
              contact us at{" "}
              <a href="mailto:support@metabrainz.org">support@metabrainz.org</a>.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

function Profile({ user, csrf_token }: ProfileProps): JSX.Element {
  return (
    <>
      <ProfileTabs activeTab="profile" />
      <h2 className="page-title">{user.name}</h2>
      {user.supporter ? (
        <SupporterProfile user={user} csrf_token={csrf_token} />
      ) : (
        <UserProfile user={user} csrf_token={csrf_token} />
      )}

      <div className="row" style={{ marginBottom: "1.5rem" }}>
        <div className="col-md-12">
          <div className="panel panel-default">
            <div className="panel-heading">
              <h3 className="panel-title">MetaBrainz Applications</h3>
            </div>
            <div className="panel-body">
              <p>
                With your MetaBrainz account, you can access every project in the
                MetaBrainz family:
              </p>
              <div className="row metabrainz-projects-list">
                <div className="col-md-3 col-sm-6">
                  <a
                    href={`https://musicbrainz.org/user/${user.name}`}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    <img src="/static/img/logos/musicbrainz.svg" alt="MusicBrainz" />
                    <div className="project-description">
                      The open-source music encyclopedia
                    </div>
                  </a>
                </div>
                <div className="col-md-3 col-sm-6">
                  <a
                    href={`https://listenbrainz.org/user/${user.name}`}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    <img src="/static/img/logos/listenbrainz.svg" alt="ListenBrainz" />
                    <div className="project-description">
                      Track, visualise and share the music you listen to
                    </div>
                  </a>
                </div>
                <div className="col-md-3 col-sm-6">
                  <a
                    href={`https://bookbrainz.org/user/${user.name}`}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    <img src="/static/img/logos/bookbrainz.svg" alt="BookBrainz" />
                    <div className="project-description">
                      The open-source book database
                    </div>
                  </a>
                </div>
                <div className="col-md-3 col-sm-6">
                  <a
                    href={`https://critiquebrainz.org/user/${user.name}`}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    <img src="/static/img/logos/critiquebrainz.svg" alt="CritiqueBrainz" />
                    <div className="project-description">
                      Creative Commons licensed reviews
                    </div>
                  </a>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {user.supporter ? (
        <SupporterAccountDeletionNotice />
      ) : (
        <DeleteAccountSection />
      )}
    </>
  );
}

document.addEventListener("DOMContentLoaded", () => {
  const { domContainer, reactProps } = getPageProps();
  const { user, csrf_token } = reactProps;

  const renderRoot = createRoot(domContainer!);
  renderRoot.render(<Profile user={user} csrf_token={csrf_token} />);
});
