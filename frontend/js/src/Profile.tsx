import React, { JSX, useCallback, useState } from "react";
import { useTranslation } from "react-i18next";
import { getPageProps, renderRoot } from "./utils";
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
  const { t } = useTranslation();
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
        {t("(Resend Verification Email)")}
      </button>
    </form>
  );

  return (
    <>
      {hasBothEmails ? (
        <>
          <strong>{t("Current:")} </strong>
          {email}{" "}
          <span className="badge" style={{ background: "green" }}>
            {t("Verified")}
          </span>
          <br />
          <strong>{t("New:")} </strong>
          {unconfirmed_email}{" "}
          <span className="badge" style={{ background: "red" }}>
            {t("Unverified")}
          </span>
          <ResendButton />
          <br />
          <small className="text-muted">
            {t(
              "Your current email will be replaced once the new email is verified."
            )}
          </small>
        </>
      ) : email ? (
        <>
          <>{email}{" "}</>
          <span className="badge" style={{ background: "green" }}>
            {t("Verified")}
          </span>
        </>
      ) : unconfirmed_email ? (
        <>
          <>{unconfirmed_email}{" "}</>
          <span className="badge" style={{ background: "red" }}>
            {t("Unverified")}
          </span>
          <ResendButton />
        </>
      ) : null}
    </>
  );
}

function SupporterProfile({ user, csrf_token }: ProfileProps) {
  const { t } = useTranslation();
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
        t(
          "Are you sure you want to generate new access token? Current token will be revoked!"
        )
      )
    ) {
      const response = await fetch("/supporters/profile/regenerate-token", {
        method: "POST",
      });
      if (!response.ok) {
        window.alert(t("Failed to generate new access token!"));
      } else {
        const data = await response.json();
        setCurrentToken(data.token);
      }
    }
  }, [currentToken, t]);

  let applicationState;
  if (state === "rejected") {
    applicationState = (
      <>
        <p>
          <b>
            {t(
              "Your application for using the Live Data Feed has been rejected."
            )}
          </b>
        </p>
        <p>
          {t(
            "You do not have permission to use our data in a public commercial product."
          )}
        </p>
      </>
    );
  } else if (state === "pending") {
    applicationState = (
      <>
        <p>
          <b>
            {t(
              "Your application for using the Live Data Feed is still pending."
            )}
          </b>
        </p>
        <p>
          {t(
            "You may use our data and APIs for evaluation/development purposes while your application is pending."
          )}
        </p>
      </>
    );
  } else if (state === "waiting") {
    applicationState = (
      <>
        <p>
          <b>
            {t(
              "Your application for using the Live Data Feed is waiting to finalize our support agreement."
            )}
          </b>
        </p>
        <p>
          {t(
            "You may use our data and APIs for evaluation and development purposes, but you may not use the data in a public commercial product. Once you are nearing the public release of a product that contains our data, please"
          )}{" "}
          <a href="/contact">{t("contact us")}</a>{" "}
          {t("again to finalize our support agreement.")}
        </p>
      </>
    );
  } else if (!good_standing) {
    applicationState = (
      <>
        <p>
          <b>{t("Your use of the Live Data Feed is pending suspension.")}</b>
        </p>
        <p>
          {t(
            "Your account is in bad standing, which means that you are more than 60 days behind in support payments. If you think this is a mistake, please"
          )}{" "}
          <a href="/contact">{t("contact us")}</a>.
        </p>
      </>
    );
  } else {
    applicationState = <p>{t("Unknown. :(")}</p>;
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

  let stateLabel;
  if (state === "active") {
    stateLabel = t("Active");
  } else if (state === "rejected") {
    stateLabel = t("Rejected");
  } else if (state === "pending") {
    stateLabel = t("Pending");
  } else if (state === "waiting") {
    stateLabel = t("Waiting");
  } else if (state === "limited") {
    stateLabel = t("Limited");
  } else {
    stateLabel = t("Unknown");
  }

  return (
    <>
      <div className="row" style={{ marginBottom: "1.5rem" }}>
        <div className="col-md-12">
          <div className="well" style={{ marginBottom: 0 }}>
            <div className="row">
              <div className="col-sm-4">
                <strong>{t("Type:")}</strong>{" "}
                {is_commercial ? t("Commercial") : t("Non-commercial")}
              </div>
              {is_commercial && (
                <div className="col-sm-4">
                  <strong>{t("Tier:")}</strong> {tier.name}
                </div>
              )}
              <div className="col-sm-4">
                <strong>{t("State:")}</strong>
                <span className={stateClass}> {stateLabel}</span>
              </div>
            </div>
          </div>
          {!is_commercial && (
            <p className="text-muted" style={{ marginTop: "0.5rem" }}>
              {t(
                "If you would like to change your account from non-commercial to commercial, please"
              )}{" "}
              <a href="/contact">{t("contact us")}</a>.
            </p>
          )}
        </div>
      </div>

      <div className="row" style={{ marginBottom: "1.5rem", display: "flex", flexWrap: "wrap" }}>
        {is_commercial && (
          <div className="col-md-6" style={{ display: "flex" }}>
            <div className="panel panel-default" style={{ flex: 1 }}>
              <div className="panel-heading">
                <h3 className="panel-title">
                  {t("Organization Information")}
                </h3>
              </div>
              <div className="panel-body">
                <dl style={{ marginBottom: 0 }}>
                  <dt>{t("Name")}</dt>
                  <dd style={{ marginBottom: "1rem" }}>
                    {org_name || (
                      <em className="text-muted">{t("Unspecified")}</em>
                    )}
                  </dd>
                  <dt>{t("Website URL")}</dt>
                  <dd style={{ marginBottom: "1rem" }}>
                    {website_url || (
                      <em className="text-muted">{t("Unspecified")}</em>
                    )}
                  </dd>
                  <dt>{t("API URL")}</dt>
                  <dd>
                    {api_url || (
                      <em className="text-muted">{t("Unspecified")}</em>
                    )}
                  </dd>
                </dl>
                <p className="text-muted" style={{ marginTop: "1rem", marginBottom: 0 }}>
                  <a href="/contact">{t("Contact us")}</a>{" "}
                  {t("to update this information.")}
                </p>
              </div>
            </div>
          </div>
        )}
        <div className={is_commercial ? "col-md-6" : "col-md-12"} style={{ display: "flex" }}>
          <div className="panel panel-default" style={{ flex: 1 }}>
            <div className="panel-heading">
              <h3 className="panel-title">{t("Contact Information")}</h3>
            </div>
            <div className="panel-body">
              <dl style={{ marginBottom: 0 }}>
                <dt>{t("Contact name")}</dt>
                <dd style={{ marginBottom: "1rem" }}>{contact_name}</dd>
                <dt>{t("Contact Email")}</dt>
                <dd style={{ marginBottom: !is_commercial ? "1rem" : 0 }}>
                  <EmailDisplay
                    email={email}
                    unconfirmed_email={unconfirmed_email}
                    csrf_token={csrf_token}
                  />
                </dd>
                {!is_commercial && (
                  <>
                    <dt>{t("Datasets Used")}</dt>
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
                  ? t("Edit Contact Information")
                  : t("Edit Datasets / Contact Information")}
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
                  <h3 className="panel-title">
                    {t("Data Use Permission Granted")}
                  </h3>
                </div>
                <div className="panel-body">
                  <p>
                    <b>
                      {t(
                        "Your support agreement has been completed -- thank you!"
                      )}
                    </b>
                  </p>
                  <p>
                    {t(
                      "You have permission to use any of the data published by the MetaBrainz Foundation. This includes data dumps released under a Creative Commons non-commercial license."
                    )}
                  </p>
                  <ul className="text-muted">
                    <li>
                      {t(
                        "If your support falls behind by more than 60 days, this permission may be withdrawn."
                      )}
                    </li>
                    <li>
                      {t(
                        "IP addresses from which replication packets are downloaded are logged."
                      )}
                    </li>
                  </ul>
                </div>
              </div>
            ) : (
              <div className="panel panel-warning">
                <div className="panel-heading">
                  <h3 className="panel-title">
                    {t("Limited/No Data Use Permission")}
                  </h3>
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
                <h3 className="panel-title">{t("Data Download")}</h3>
              </div>
              <div className="panel-body">
                {!is_commercial && (
                  <p>
                    {t(
                      "Thank you for registering with us -- we really appreciate it!"
                    )}
                  </p>
                )}
                <p>{t("Proceed to our download page to download datasets:")}</p>
                <a href="/download" className="btn btn-primary">
                  {t("Download Datasets")}
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
                <h3 className="panel-title">
                  {t("Live Data Feed Access Token")}
                </h3>
              </div>
              <div className="panel-body">
                <p className="text-muted" style={{ fontStyle: "italic" }}>
                  {t(
                    "This access token should be considered private. Don't check it into publicly visible version control systems. If exposed, generate a new one immediately."
                  )}
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
                  {currentToken || t("[ no valid token currently ]")}
                </div>
                <button
                  className="btn btn-default"
                  type="button"
                  onClick={regenerateToken}
                >
                  {t("Generate New Token")}
                </button>
                <p style={{ marginTop: "1rem", marginBottom: 0 }}>
                  {t("See the")} <a href="/api">{t("API documentation")}</a>{" "}
                  {t("for more information.")}
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
  const { t } = useTranslation();
  const { name, email, unconfirmed_email } = user;
  return (
    <>
      <div className="row" style={{ marginBottom: "1.5rem" }}>
        <div className="col-md-12">
          <div className="panel panel-default">
            <div className="panel-heading">
              <h3 className="panel-title">{t("Contact Information")}</h3>
            </div>
            <div className="panel-body">
              <dl style={{ marginBottom: 0 }}>
                <dt>{t("Name")}</dt>
                <dd style={{ marginBottom: "1rem" }}>{name}</dd>
                <dt>{t("Email")}</dt>
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
                {t("Edit Information")}
              </a>
            </div>
          </div>
        </div>
      </div>

      <div className="row" style={{ marginBottom: "1.5rem" }}>
        <div className="col-md-12">
          <div className="panel panel-info">
            <div className="panel-heading">
              <h3 className="panel-title">
                {t("Want access to MetaBrainz datasets?")}
              </h3>
            </div>
            <div className="panel-body">
              <p>
                {t(
                  "Upgrade your account to a supporter account to access our datasets and the Live Data Feed. Choose between non-commercial (free) and commercial options."
                )}
              </p>
              <a href="/supporters/account-type" className="btn btn-primary">
                {t("Become a Supporter")}
              </a>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

function DeleteAccountSection() {
  const { t } = useTranslation();

  return (
    <div className="row" style={{ marginBottom: "1.5rem" }}>
      <div className="col-md-12">
        <div className="panel panel-danger">
          <div className="panel-heading">
            <h3 className="panel-title">{t("Danger Zone")}</h3>
          </div>
          <div className="panel-body">
            <p>
              <strong>{t("Delete your account")}</strong>
            </p>
            <p className="text-muted">
              {t(
                "Once you delete your account, there is no going back. Please be certain."
              )}
            </p>
            <a href="/profile/delete" className="btn btn-danger">
              {t("Delete My Account")}
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}

function SupporterAccountDeletionNotice() {
  const { t } = useTranslation();

  return (
    <div className="row" style={{ marginBottom: "1.5rem" }}>
      <div className="col-md-12">
        <div className="panel panel-default">
          <div className="panel-heading">
            <h3 className="panel-title">{t("Account Deletion")}</h3>
          </div>
          <div className="panel-body">
            <p>
              <strong>{t("Need to delete your account?")}</strong>
            </p>
            <p className="text-muted" style={{ marginBottom: 0 }}>
              {t(
                "Deletion of supporter accounts requires manual review. Please contact us at"
              )}{" "}
              <a href="mailto:support@metabrainz.org">support@metabrainz.org</a>.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

function SecuritySection() {
  const { t } = useTranslation();

  return (
    <div className="row" style={{ marginBottom: "1.5rem" }}>
      <div className="col-md-12">
        <div className="panel panel-default">
          <div className="panel-heading">
            <h3 className="panel-title">{t("Security")}</h3>
          </div>
          <div className="panel-body">
            <a href="/profile/change-password" className="btn btn-warning">
              {t("Change Password")}
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}

function Profile({ user, csrf_token }: ProfileProps): JSX.Element {
  const { t } = useTranslation();

  return (
    <>
      <ProfileTabs activeTab="profile" />
      <h2 className="page-title">{user.name}</h2>
      {user.supporter ? (
        <SupporterProfile user={user} csrf_token={csrf_token} />
      ) : (
        <UserProfile user={user} csrf_token={csrf_token} />
      )}

      <SecuritySection />

      <div className="row" style={{ marginBottom: "1.5rem" }}>
        <div className="col-md-12">
          <div className="panel panel-default">
            <div className="panel-heading">
              <h3 className="panel-title">{t("MetaBrainz Applications")}</h3>
            </div>
            <div className="panel-body">
              <p>
                {t(
                  "With your MetaBrainz account, you can access every project in the MetaBrainz family:"
                )}
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
                      {t("The open-source music encyclopedia")}
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
                      {t("Track, visualise and share the music you listen to")}
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
                      {t("The open-source book database")}
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
                      {t("Creative Commons licensed reviews")}
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

  renderRoot(
    domContainer!,
    <Profile user={user} csrf_token={csrf_token} />);
});
