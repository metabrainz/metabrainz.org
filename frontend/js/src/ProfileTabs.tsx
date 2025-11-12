import React from "react";

type ProfileTabsProps = {
  activeTab: "profile" | "applications";
};

export default function ProfileTabs({
  activeTab,
}: ProfileTabsProps): JSX.Element {
  const isActive = (tab: ProfileTabsProps["activeTab"]) => activeTab === tab;
  return (
    <ul className="nav nav-tabs">
      <li className={`nav-item ${isActive("profile") ? "active" : ""}`}>
        <a className="nav-link" aria-current="page" href="/profile">
          Profile
        </a>
      </li>
      <li className={`nav-item ${isActive("applications") ? "active" : ""}`}>
        <a className="nav-link" href="/profile/applications">
          Applications
        </a>
      </li>
    </ul>
  );
}
