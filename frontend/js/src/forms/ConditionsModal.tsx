import React from "react";
import { useTranslation } from "react-i18next";
import PrivacySummaryContent from "./PrivacySummaryContent";

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
            <h4 className="modal-title">{t("Privacy Policy")}</h4>
          </div>
          <PrivacySummaryContent />
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
