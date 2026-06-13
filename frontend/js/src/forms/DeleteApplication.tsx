import React, { JSX } from "react";
import { useTranslation } from "react-i18next";
import { getPageProps, renderRoot } from "../utils";

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
  const { t } = useTranslation();

  return (
    <>
      <h2>{t("Delete application")}</h2>
      <hr />
      <div className="panel panel-danger">
        <div className="panel-heading">
          <h3 className="panel-title">{t("Client Details")}</h3>
        </div>
        <div className="panel-body">
          <dl>
            <dt>{t("Name:")}</dt>
            <dd>{application.name}</dd>
            <dt>{t("Description:")}</dt>
            <dd>{application.description}</dd>
            <dt>{t("Website:")}</dt>
            <dd>
              <a href={`${application.website}`}>{application.website}</a>
            </dd>
          </dl>
          <p>{t("Are you sure you want to delete this client?")}</p>
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
            <div className="form-group">
              <div className="col-sm-offset-4 col-sm-8">
                <a href={cancel_url} className="btn btn-default">
                  {t("Cancel")}
                </a>
                <button
                  type="submit"
                  className="btn btn-danger"
                  style={{ marginLeft: "8px" }}
                >
                  {t("Delete")}
                </button>
              </div>
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

  renderRoot(
    domContainer!,
    <DeleteApplication
      csrf_token={csrf_token}
      cancel_url={cancel_url}
      application={application}
    />
  );
});
