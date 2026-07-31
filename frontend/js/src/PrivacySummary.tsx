import React, { JSX } from "react";
import { useTranslation } from "react-i18next";
import PrivacySummaryContent from "./forms/PrivacySummaryContent";
import { getPageProps, renderRoot } from "./utils";

function PrivacySummary(): JSX.Element {
  const { t } = useTranslation();

  return (
    <div className="well well-lg" style={{ maxWidth: "800px", margin: "0 auto" }}>
      <h2 className="page-title">{t("Privacy Policy")}</h2>
      <hr/>
      <PrivacySummaryContent />
    </div>
  );
}

document.addEventListener("DOMContentLoaded", () => {
  const { domContainer } = getPageProps();

  renderRoot(domContainer, <PrivacySummary />);
});
