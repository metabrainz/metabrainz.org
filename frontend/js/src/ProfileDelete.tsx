import React, { useState, useCallback } from "react";
import { Trans, useTranslation } from "react-i18next";
import { getPageProps, renderRoot } from "./utils";

type ProfileDeleteProps = {
  csrf_token: string;
  username: string;
};

function ProfileDelete({ csrf_token, username }: ProfileDeleteProps) {
  const { t } = useTranslation();
  const [isDeleting, setIsDeleting] = useState(false);
  const [confirmText, setConfirmText] = useState("");

  const isConfirmValid = confirmText === username;

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();

      if (!isConfirmValid) {
        return;
      }

      const confirmed = window.confirm(
        t(
          "Are you sure you want to delete your account? This action cannot be undone."
        )
      );

      if (!confirmed) {
        return;
      }

      setIsDeleting(true);

      const form = e.target as HTMLFormElement;
      form.submit();
    },
    [isConfirmValid, t]
  );

  return (
    <div className="row">
      <div className="col-md-8 col-md-offset-2">
        <h2 className="page-title">{t("Delete your account")}</h2>

        <div
          className="panel panel-danger"
          style={{ borderColor: "#d9534f" }}
        >
          <div
            className="panel-heading"
            style={{ backgroundColor: "#d9534f", color: "white" }}
          >
            <h3 className="panel-title">
              {t("Warning: This action is irreversible")}
            </h3>
          </div>
          <div className="panel-body">
            <p>{t("Deleting your account will:")}</p>
            <ul>
              <li>{t("Permanently remove all your account information")}</li>
              <li>{t("Revoke all your API tokens and access")}</li>
              <li>{t("Remove your supporter status (if applicable)")}</li>
              <li>{t("Log you out of all MetaBrainz services")}</li>
            </ul>
            <p>
              <strong>
                {t(
                  "Your username will be reserved and cannot be reused without the intervention of an administrator."
                )}
              </strong>
            </p>

            <hr />

            <form method="POST" onSubmit={handleSubmit}>
              <input type="hidden" name="csrf_token" value={csrf_token} />

              <div className="form-group">
                <label htmlFor="confirm-username">
                  <Trans
                    defaults={t(
                      "To confirm, type your username '<username />' below:"
                    )}
                    components={{username: <strong>{username}</strong>}}
                  />
                </label>
                <input
                  type="text"
                  id="confirm-username"
                  className="form-control"
                  value={confirmText}
                  onChange={(e) => setConfirmText(e.target.value)}
                  autoComplete="off"
                  disabled={isDeleting}
                />
              </div>

              <div style={{ display: "flex", gap: "1rem", marginTop: "1.5rem" }}>
                <button
                  type="submit"
                  className="btn btn-danger"
                  disabled={!isConfirmValid || isDeleting}
                >
                  {isDeleting ? t("Deleting...") : t("Delete My Account")}
                </button>
                <a href="/profile" className="btn btn-default">
                  {t("Cancel")}
                </a>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}

document.addEventListener("DOMContentLoaded", () => {
  const { domContainer, reactProps } = getPageProps();
  const { csrf_token, username } = reactProps;

  renderRoot(
    domContainer!,
    <ProfileDelete csrf_token={csrf_token} username={username} />);
});
