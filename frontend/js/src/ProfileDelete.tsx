import React, { useState, useCallback } from "react";
import { createRoot } from "react-dom/client";
import { getPageProps } from "./utils";

type ProfileDeleteProps = {
  csrf_token: string;
  username: string;
};

function ProfileDelete({ csrf_token, username }: ProfileDeleteProps) {
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
        "Are you sure you want to delete your account? This action cannot be undone."
      );

      if (!confirmed) {
        return;
      }

      setIsDeleting(true);

      const form = e.target as HTMLFormElement;
      form.submit();
    },
    [isConfirmValid]
  );

  return (
    <div className="row">
      <div className="col-md-8 col-md-offset-2">
        <h2 className="page-title">Delete Your Account</h2>

        <div
          className="panel panel-danger"
          style={{ borderColor: "#d9534f" }}
        >
          <div
            className="panel-heading"
            style={{ backgroundColor: "#d9534f", color: "white" }}
          >
            <h3 className="panel-title">Warning: This action is irreversible</h3>
          </div>
          <div className="panel-body">
            <p>Deleting your account will:</p>
            <ul>
              <li>Permanently remove all your account information</li>
              <li>Revoke all your API tokens and access</li>
              <li>Remove your supporter status (if applicable)</li>
              <li>Log you out of all MetaBrainz services</li>
            </ul>
            <p>
              <strong>Your username will be reserved and cannot be reused.</strong>
            </p>

            <hr />

            <form method="POST" onSubmit={handleSubmit}>
              <input type="hidden" name="csrf_token" value={csrf_token} />

              <div className="form-group">
                <label htmlFor="confirm-username">
                  To confirm, type your username <strong>{username}</strong> below:
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
                  {isDeleting ? "Deleting..." : "Delete My Account"}
                </button>
                <a href="/profile" className="btn btn-default">
                  Cancel
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

  const renderRoot = createRoot(domContainer!);
  renderRoot.render(<ProfileDelete csrf_token={csrf_token} username={username} />);
});
