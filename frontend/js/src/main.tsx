import React from "react";
import { createRoot } from "react-dom/client";
import { getPageProps } from "./utils";

function App() {
  return (
    <div className="App">
      <header className="App-header">
        <img src="/static/img/logo.svg" className="App-logo" alt="logo" />
        <p>
          Edit <code>src/App.tsx</code> and save to reload.
        </p>
        <a
          className="App-link"
          href="https://reactjs.org"
          target="_blank"
          rel="noopener noreferrer"
        >
          Learn React
        </a>
      </header>
    </div>
  );
}

document.addEventListener("DOMContentLoaded", () => {
  const { domContainer, reactProps, globalProps } = getPageProps();

  const root = createRoot(domContainer!);
  root.render(<App />);
});
