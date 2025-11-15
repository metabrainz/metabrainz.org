import React from "react";

type Application = {
  name: string;
  website: string;
  client_id: string;
  client_secret: string;
};

type ApplicationRowProps = {
  urlPrefix: string;
  application: Application;
};

function ApplicationRow({
  application,
  urlPrefix,
}: ApplicationRowProps): JSX.Element {
  const { name, website, client_id, client_secret } = application;
  const [passwordVisible, setPasswordVisible] = React.useState(false);
  const glyphIcon = passwordVisible
    ? "glyphicon-eye-close"
    : "glyphicon-eye-open";
  const title = passwordVisible ? "Hide password" : "Show password";
  const passwordShowButton = (
    <button
      className="btn btn-info btn-xs pull-right"
      style={{ outline: "none" }}
      title={title}
      type="button"
      onClick={() => {
        setPasswordVisible((prev) => !prev);
      }}
    >
      <span className={`glyphicon ${glyphIcon}`} aria-hidden="true" />
    </button>
  );

  const secret = passwordVisible
    ? client_secret
    : "*".repeat(client_secret.length);

  return (
    <tr>
      <td>{name}</td>
      <td>{website}</td>
      <td>{client_id}</td>
      <td>
        {secret} {passwordShowButton}
      </td>
      <td>
        <a
          className="btn btn-block btn-warning btn-xs"
          href={`${urlPrefix}/client/edit/${client_id}`}
        >
          Modify
        </a>
        <a
          className="btn btn-block btn-danger btn-xs"
          href={`${urlPrefix}/client/delete/${client_id}`}
        >
          Delete
        </a>
      </td>
    </tr>
  );
}

export default ApplicationRow;
