import { Formik } from "formik";
import React, { JSX } from "react";
import { useTranslation } from "react-i18next";
import * as Yup from "yup";
import { getPageProps, renderRoot } from "../utils";
import {
  AuthCardContainer,
  AuthCardPasswordInput,
} from "./utils";

type ResetPasswordProps = {
  csrf_token: string;
  initial_errors: any;
};

function ResetPassword({
  csrf_token,
  initial_errors,
}: ResetPasswordProps): JSX.Element {
  const { t } = useTranslation();

  return (
    <AuthCardContainer>
      <div className="auth-card-container">
        <div className="auth-card">
          <h1 className="page-title text-center">
            {t("Reset your password")}
          </h1>
          <Formik
            initialValues={{
              password: "",
              confirm_password: "",
              csrf_token,
            }}
            initialErrors={initial_errors}
            initialTouched={initial_errors}
            validationSchema={Yup.object({
              password: Yup.string()
                .required(t("Password is required!"))
                .min(8)
                .max(64),
              confirm_password: Yup.string()
                .required()
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
              <form method="POST">
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
                    <div className="alert alert-danger">
                      {errors.csrf_token}
                    </div>
                  )}
                </div>

                <AuthCardPasswordInput
                  label={t("Password")}
                  name="password"
                  id="password"
                  required
                />

                <AuthCardPasswordInput
                  label={t("Confirm Password")}
                  name="confirm_password"
                  id="confirm_password"
                  required
                />

                <button
                  className="btn btn-primary main-action-button"
                  type="submit"
                >
                  {t("Reset Password")}
                </button>
              </form>
            )}
          </Formik>
        </div>
      </div>
    </AuthCardContainer>
  );
}

document.addEventListener("DOMContentLoaded", () => {
  const { domContainer, reactProps } = getPageProps();
  const { csrf_token, initial_errors } = reactProps;

  renderRoot(
    domContainer!,
    <ResetPassword csrf_token={csrf_token} initial_errors={initial_errors} />
  );
});
