import React, { JSX } from "react";
import { createRoot } from "react-dom/client";
import { getPageProps } from "./utils";

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

  const renderRoot = createRoot(domContainer!);
  renderRoot.render(<OAuthError error={error} />);
});
