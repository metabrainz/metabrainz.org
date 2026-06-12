import React from "react";
import { useTranslation } from "react-i18next";
import { ProjectIconPills } from "./utils";

export default function ConditionsModal() {
  const { t } = useTranslation();

  return (
    <div className="modal fade" id="conditions-modal">
      <div className="modal-dialog" role="document">
        <div className="modal-content">
          <div className="modal-header">
            <button
              type="button"
              className="close"
              data-dismiss="modal"
              aria-label={t("Close")}
            >
              <span aria-hidden="true">&times;</span>
            </button>
            <h4 className="modal-title">{t("Privacy policy")}</h4>
          </div>
          <h5>{t("Licensing")}</h5>
          <p>
            {t(
              "Any contributions you make to MusicBrainz will be released into the Public Domain and/or licensed under a Creative Commons by-nc-sa license. Furthermore, you give the MetaBrainz Foundation the right to license this data for commercial use."
            )}
            <br />
            {t("Please read our")}{" "}
            <a
              target="_blank"
              rel="noopener noreferrer"
              href="/social-contract"
            >
              {t("license page")}
            </a>{" "}
            {t("for more details.")}
          </p>
          <h5>{t("Privacy")}</h5>
          <p>
            {t(
              "MusicBrainz strongly believes in the privacy of its users. Any personal information you choose to provide will not be sold or shared with anyone else."
            )}
            <br />
            {t("Please read our")}{" "}
            <a target="_blank" rel="noopener noreferrer" href="/privacy">
              {t("privacy policy")}
            </a>{" "}
            {t("for more details.")}
          </p>
          <h5>{t("GDPR compliance")}</h5>
          <p>
            {t(
              "You may remove your personal information from our services anytime by deleting your account."
            )}
            <br />
            {t("Please read our")}{" "}
            <a target="_blank" rel="noopener noreferrer" href="/gdpr">
              {t("GDPR compliance statement")}
            </a>{" "}
            {t("for more details.")}
          </p>
          <hr />
          <ProjectIconPills />
          <p>
            {t(
              "Creating an account on MetaBrainz will give you access to all of our projects, such as MusicBrainz, ListenBrainz, BookBrainz, and more."
            )}
            <br />
            {t(
              "We do not automatically create accounts for these services when you create a MetaBrainz account, but you will be just a few clicks away from doing so."
            )}
          </p>
          <button
            className="btn btn-primary center-block"
            type="button"
            data-dismiss="modal"
          >
            {t("Sounds good")}
          </button>
        </div>
      </div>
    </div>
  );
}
