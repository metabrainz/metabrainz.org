import { Formik } from "formik";
import React, { JSX } from "react";
import { useTranslation } from "react-i18next";
import * as Yup from "yup";
import { getPageProps, renderRoot } from "../utils";
import { TextInput } from "./utils";

type ProfileChangePasswordProps = {
  csrf_token: string;
  initial_errors: any;
};

function ProfileChangePassword({
  csrf_token,
  initial_errors,
}: ProfileChangePasswordProps): JSX.Element {
  const { t } = useTranslation();

  return (
    <>
      <h1 className="page-title">{t("Your Profile")}</h1>
      <h2>{t("Change Password")}</h2>
      <Formik
        initialValues={{
          current_password: "",
          password: "",
          confirm_password: "",
          csrf_token,
        }}
        initialErrors={initial_errors}
        initialTouched={initial_errors}
        validationSchema={Yup.object({
          current_password: Yup.string().required(
            t("Current password is required!")
          ),
          password: Yup.string()
            .required(t("Password is required!"))
            .min(8)
            .max(64),
          confirm_password: Yup.string()
            .required(t("Confirm Password is required!"))
            .min(8)
            .max(64)
            .oneOf(
              [Yup.ref("password")],
              t("Confirm Password should match password!")
            ),
        })}
        onSubmit={() => {}}
      >
        {({ errors }) => (
          <form method="POST" className="form-horizontal">
            <div className="form-group">
              <div className="col-sm-offset-4 col-sm-5">
                <input
                  id="csrf_token"
                  name="csrf_token"
                  type="hidden"
                  value={csrf_token}
                />
              </div>
              {errors.csrf_token && (
                <div className="alert alert-danger">{errors.csrf_token}</div>
              )}
            </div>

            <TextInput
              type="password"
              id="current_password"
              name="current_password"
              label={t("Current Password")}
              autoComplete="current-password"
              required
            />

            <TextInput
              type="password"
              id="password"
              name="password"
              label={t("New Password")}
              autoComplete="new-password"
              required
            />

            <TextInput
              type="password"
              id="confirm_password"
              name="confirm_password"
              label={t("Confirm New Password")}
              autoComplete="new-password"
              required
            />

            <div className="form-group">
              <div
                className="col-sm-offset-4 col-sm-5"
                style={{ display: "flex", gap: "10px" }}
              >
                <a
                  href="/profile"
                  className="btn btn-default"
                  style={{ flex: 1, textAlign: "center" }}
                >
                  {t("Cancel")}
                </a>
                <button
                  type="submit"
                  className="btn btn-primary"
                  style={{ flex: 1 }}
                >
                  {t("Change Password")}
                </button>
              </div>
            </div>
          </form>
        )}
      </Formik>
    </>
  );
}

document.addEventListener("DOMContentLoaded", () => {
  const { domContainer, reactProps } = getPageProps();
  const { csrf_token, initial_errors } = reactProps;

  renderRoot(
    domContainer!,
    <ProfileChangePassword
      csrf_token={csrf_token}
      initial_errors={initial_errors}
    />
  );
});
