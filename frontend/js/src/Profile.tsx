import React, { JSX, useCallback, useState } from "react";
import { createRoot } from "react-dom/client";
import { getPageProps } from "./utils";

type ProfileProps = {
  user: User;
  csrf_token?: string;
};

type EmailProps = {
  label: string;
  is_email_confirmed: boolean;
  email: string;
  csrf_token?: string;
};

function Email({
  label,
  is_email_confirmed,
  email,
  csrf_token,
}: EmailProps): JSX.Element {
  return (
    <>
      <strong>{label}:</strong> {email}{" "}
      {is_email_confirmed ? (
        <span className="badge" style={{ background: "green" }}>
          Verified
        </span>
      ) : (
        <>
          <span className="badge" style={{ background: "red" }}>
            Unverified
          </span>
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
            <button className="btn btn-link text-danger" type="submit">
              (Resend Verification Email)
            </button>
          </form>
        </>
      )}
      <br />
    </>
  );
}

function SupporterProfile({ user, csrf_token }: ProfileProps) {
  const { email, is_email_confirmed, supporter } = user;
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
  } = supporter!!;
  const [currentToken, setCurrentToken] = useState(token);

  const regenerateToken = useCallback(async () => {
    if (
      !currentToken ||
      // eslint-disable-next-line no-alert
      window.confirm(
        "Are you sure you want to generate new access token? Current token will be revoked!"
      )
    ) {
      const response = await fetch("/supporters/profile/regenerate-token", {
        method: "POST",
      });
      if (!response.ok) {
        // eslint-disable-next-line no-alert
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
      <p>
        <strong>Type:</strong> {is_commercial ? "Commercial" : "Non-commercial"}
        <br />
        {is_commercial && (
          <>
            <strong>Tier:</strong> {tier.name}
            <br />
          </>
        )}
        <strong>State:</strong>
        <span className={stateClass}> {state.toUpperCase()}</span>
      </p>
      {!is_commercial && (
        <p>
          NOTE: If you would like to change your account from non-commercial to
          commercial, please
          <a href="/contact">contact us</a>.
        </p>
      )}
      <div className="row">
        {is_commercial && (
          <div className="col-md-7">
            <h3>Organization information</h3>
            <p>
              <strong>Name:</strong>{" "}
              {org_name || <em className="text-muted">Unspecified</em>}
              <br />
              <strong>Website URL:</strong>{" "}
              {website_url || <em className="text-muted">Unspecified</em>}
              <br />
              <strong>API URL:</strong>{" "}
              {api_url || <em className="text-muted">Unspecified</em>}
              <br />
            </p>
            <p>
              Please <a href="/contact">contact us</a> if you wish for us to
              update this information.
            </p>
          </div>
        )}
        <div className="col-md-12">
          <h3>Contact information</h3>
          <p>
            <strong>Contact Name:</strong> {contact_name}
            <br />
            <Email
              label="Contact Email"
              is_email_confirmed={is_email_confirmed}
              email={email}
              csrf_token={csrf_token}
            />
            {!is_commercial && (
              <>
                <strong>Datasets used:</strong>{" "}
                {datasets.map((d) => d.name).join(", ")}
                <br />
              </>
            )}
          </p>
          <p>
            <a href="/profile/edit" className="btn btn-lg btn-primary">
              {is_commercial
                ? "Edit contact information"
                : "Edit datasets/contact information"}
            </a>
          </p>
        </div>
      </div>
      {is_commercial &&
        ((state === "active" || state === "limited") && good_standing ? (
          <>
            <h3>Data use permission granted</h3>
            <div style={{ fontSize: "13pt" }}>
              <p>
                <b>Your support agreement has been completed -- thank you!</b>
              </p>
              <p>
                You have permission to use any of the data published by the
                MetaBrainz Foundation. This includes data dumps released under a
                Creative Commons non-commercial license. Thank you for your
                support!
              </p>
              <p>
                Note 1: If your support falls behind by more than 60 days, this
                permission may be withdrawn. You can always check your current
                permission status on this page.
              </p>
              <p>
                Note 2: The IP addresses from which replication packets for the
                Live Data Feed are downloaded are logged.
              </p>
            </div>
          </>
        ) : (
          <>
            <h3>Limited/no data use permission granted</h3>
            <div style={{ fontSize: "13pt" }}>{applicationState}</div>
          </>
        ))}
      {(state === "active" || state === "limited") && good_standing && (
        <>
          <h2>Data Download</h2>
          <div style={{ fontSize: "13pt" }}>
            {!is_commercial && (
              <p>
                Thank you for registering with us -- we really appreciate it!
              </p>
            )}
            <p>Please proceed to our download page to download our datasets:</p>
            <p>
              <a href="/download" className="btn btn-lg btn-primary">
                Download Datasets
              </a>
            </p>
          </div>
        </>
      )}
      {state === "active" && (
        <>
          <h2>Live Data Feed Access token</h2>
          <p style={{ fontStyle: "italic", color: "#444" }}>
            This access token should be considered private. Don&apos;t check
            this token into any publicly visible version control systems and
            similar places. If the token has been exposed, you should
            immediately immediately generate a new one! When you generate a new
            token, your token is revoked.
          </p>
          <div className="dataset-summary">
            <p>
              <div
                id="token"
                style={{
                  fontSize: "14pt",
                  padding: ".5em",
                  color: "#AA0000",
                }}
              >
                {currentToken || "[ there is no valid token currently ]"}
              </div>
            </p>
            <p>
              <button
                id="btn-generate-token"
                className="btn btn-default"
                type="button"
                onClick={regenerateToken}
              >
                Generate new token
              </button>
            </p>
          </div>
          <p>
            See the <a href="/api">API documentation</a> for more information.
          </p>
        </>
      )}
    </>
  );
}

function UserProfile({ user, csrf_token }: ProfileProps): JSX.Element {
  const { name, is_email_confirmed, email } = user;
  return (
    <>
      <h3>Contact information</h3>
      <p>
        <strong>Name:</strong> {name}
        <br />
        <Email
          label="Email"
          is_email_confirmed={is_email_confirmed}
          email={email}
          csrf_token={csrf_token}
        />
      </p>
      <p>
        <a href="/profile/edit" className="btn btn-lg btn-primary">
          Edit information
        </a>
      </p>
    </>
  );
}

function Profile({ user, csrf_token }: ProfileProps): JSX.Element {
  return (
    <>
      <h1 className="page-title">Your Profile</h1>
      {user.supporter ? (
        <SupporterProfile user={user} csrf_token={csrf_token} />
      ) : (
        <UserProfile user={user} csrf_token={csrf_token} />
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
