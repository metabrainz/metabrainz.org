import React, { JSX } from "react";
import { getPageProps, renderRoot } from "./utils";

type OAuthErrorProps = {
  error: {
    name: string;
    description: string;
  };
};

function OAuthError({ error }: OAuthErrorProps): JSX.Element {
  return (
    <>
      <h1>OAuth2 Error</h1>
      <p>An error occurred during OAuth authentication process.</p>
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
