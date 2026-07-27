import React, { JSX } from "react";
import { useTranslation } from "react-i18next";
import { getPageProps, renderRoot } from "./utils";

type OAuthErrorProps = {
  error: {
    name: string;
    description: string;
  };
};

function OAuthError({ error }: OAuthErrorProps): JSX.Element {
  const { t } = useTranslation();

  return (
    <>
      <h1>{t("OAuth2 Error")}</h1>
      <p>{t("An error occurred during OAuth authentication process.")}</p>
      <p>
        {error.name}: {error.description}
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
