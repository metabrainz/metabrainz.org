import React from "react";
import { createRoot } from "react-dom/client";
import { I18nextProvider } from "react-i18next";
import i18next from "i18next";
import { initI18n } from "./i18n";

const getPageProps = (): {
  domContainer: HTMLElement;
  reactProps: Record<string, any>;
  globalProps: Record<string, any>;
} => {
  let domContainer = document.getElementById("react-container");
  const propsElement = document.getElementById("page-react-props");
  const globalPropsElement = document.getElementById("global-react-props");
  let reactProps = {};
  let globalProps = {};
  if (!domContainer) {
    // Ensure there is a container for React rendering
    // We should always have on the page already, but displaying errors to the user relies on there being one
    domContainer = document.createElement("div");
    domContainer.id = "react-container";
    const container = document.getElementsByClassName("wrapper");
    container[0].appendChild(domContainer);
  }
  // Global props *cannot* be empty
  if (globalPropsElement?.innerHTML) {
    globalProps = JSON.parse(globalPropsElement.innerHTML);
  } else {
    throw new Error("No global props element found on the page");
  }
  // Page props can be empty
  if (propsElement?.innerHTML) {
    reactProps = JSON.parse(propsElement!.innerHTML);
  }

  initI18n(globalProps);

  return {
    domContainer,
    reactProps,
    globalProps,
  };
};

const renderRoot = (
  domContainer: HTMLElement,
  element: React.ReactElement
) => {
  const root = createRoot(domContainer);
  root.render(<I18nextProvider i18n={i18next}>{element}</I18nextProvider>);
};

export { getPageProps, renderRoot };
