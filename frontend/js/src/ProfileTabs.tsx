import React from "react";
import { useTranslation } from "react-i18next";

type ProfileTabsProps = {
  activeTab: "profile" | "applications";
};

export default function ProfileTabs({
  activeTab,
}: ProfileTabsProps): React.JSX.Element {
  const { t } = useTranslation();
  const isActive = (tab: ProfileTabsProps["activeTab"]) => activeTab === tab;
  return (
    <ul className="nav nav-tabs">
      <li className={`nav-item ${isActive("profile") ? "active" : ""}`}>
        <a className="nav-link" aria-current="page" href="/profile">
          {t("Profile")}
        </a>
      </li>
      <li className={`nav-item ${isActive("applications") ? "active" : ""}`}>
        <a className="nav-link" href="/profile/applications">
          {t("Applications")}
        </a>
      </li>
    </ul>
  );
}
