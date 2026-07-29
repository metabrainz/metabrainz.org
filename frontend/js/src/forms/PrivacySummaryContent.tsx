import React, { JSX } from "react";
import { Trans, useTranslation } from "react-i18next";
import { ProjectIconPills } from "./utils";

export default function PrivacySummaryContent(): JSX.Element {
  const { t } = useTranslation();

  return (
    <>
      <h5>{t("Licensing")}</h5>
      <p>
        {t(
          "Any contributions you make to any MetaBrainz service will be released into the Public Domain and/or licensed under a Creative Commons by-nc-sa license. Furthermore, you give the MetaBrainz Foundation the right to license this data for commercial use."
        )}
        <br />
        <Trans
          defaults={t(
            "Please read our <licenseLink>license page</licenseLink> for more details."
          )}
          components={{
            licenseLink: (
              // eslint-disable-next-line jsx-a11y/anchor-has-content
              <a
                target="_blank"
                rel="noopener noreferrer"
                href="/social-contract"
              />
            ),
          }}
        />
      </p>
      <h5>{t("Privacy")}</h5>
      <p>
        {t(
          "MetaBrainz strongly believes in the privacy of its users. Any personal information you choose to provide will not be sold or shared with anyone else."
        )}
        <br />
        <Trans
          defaults={t(
            "Please read our <privacyLink>privacy policy</privacyLink> for more details."
          )}
          components={{
            privacyLink: (
              // eslint-disable-next-line jsx-a11y/anchor-has-content
              <a target="_blank" rel="noopener noreferrer" href="/privacy" />
            ),
          }}
        />
      </p>
      <h5>{t("GDPR compliance")}</h5>
      <p>
        {t(
          "You may remove your personal information from our services anytime by deleting your account."
        )}
        <br />
        <Trans
          defaults={t(
            "Please read our <gdprLink>GDPR compliance statement</gdprLink> for more details."
          )}
          components={{
            gdprLink: (
              // eslint-disable-next-line jsx-a11y/anchor-has-content
              <a target="_blank" rel="noopener noreferrer" href="/gdpr" />
            ),
          }}
        />
      </p>
      <hr />
      <ProjectIconPills />
      <p>
        {t(
          "Creating an account on MetaBrainz will give you access to all of our projects, such as MusicBrainz, ListenBrainz, BookBrainz, and more."
        )}
        <br />
        {t(
          "We create a placeholder account for all the MetaBrainz projects when you sign up, and you are one log-in away from activating them."
        )}
      </p>
    </>
  );
}
