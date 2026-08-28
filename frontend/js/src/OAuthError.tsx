import React, { JSX } from "react";
import { useTranslation } from "react-i18next";
import { getPageProps, renderRoot } from "./utils";

type OAuthErrorProps = {
  error: {
    name: string;
    description: string;
    message?: string | null;
  };
};

function OAuthError({ error }: OAuthErrorProps): JSX.Element {
  const { t } = useTranslation();

  return (
    <>
      <h1>{t("OAuth2 Error")}</h1>
      <p>{error.message || t("An error occurred during OAuth authentication process.")}</p>
      <p className="text-muted">
        <small>
          {error.name}: {error.description}
        </small>
      </p>
    </>
  );
}

document.addEventListener("DOMContentLoaded", () => {
  const { domContainer, reactProps } = getPageProps();
  const { error } = reactProps;

  renderRoot(
    domContainer!,
    <OAuthError error={error} />);
});
