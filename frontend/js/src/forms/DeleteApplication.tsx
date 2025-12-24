import React, { JSX } from "react";
import { createRoot } from "react-dom/client";
import { getPageProps } from "../utils";

type DeleteApplicationProps = {
  csrf_token: string;
  cancel_url: string;
  application: Application;
};

function DeleteApplication({
  csrf_token,
  cancel_url,
  application,
}: DeleteApplicationProps): JSX.Element {
  return (
    <>
      <h2>Delete application</h2>
      <hr />
      <div className="card">
        <div className="card-body">
          <h5 className="card-title">Client Details</h5>
          <p className="card-text">
            <strong>Name:</strong> {application.name}
          </p>
          <p className="card-text">
            <strong>Description:</strong> {application.description}
          </p>
          <p className="card-text">
            <strong>Website:</strong>{" "}
            <a href={`${application.website}`}>{application.website}</a>
          </p>
          <p>Are you sure you want to delete this client?</p>
          <form method="POST" className="form-horizontal">
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
            <div className="btn-group">
              <a href={cancel_url} className="btn btn-default">
                Cancel
              </a>
              <button
                type="submit"
                className="btn btn-danger"
                style={{ marginLeft: "8px" }}
              >
                Delete
              </button>
            </div>
          </form>
        </div>
      </div>
    </>
  );
}

document.addEventListener("DOMContentLoaded", () => {
  const { domContainer, reactProps } = getPageProps();
  const { csrf_token, cancel_url, application } = reactProps;

  const renderRoot = createRoot(domContainer!);
  renderRoot.render(
    <DeleteApplication
      csrf_token={csrf_token}
      cancel_url={cancel_url}
      application={application}
    />
  );
});
