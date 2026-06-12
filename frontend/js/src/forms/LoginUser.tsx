import { Formik } from "formik";
import React, { JSX } from "react";
import { useTranslation } from "react-i18next";
import * as Yup from "yup";
import { getPageProps, renderRoot } from "../utils";
import {
  AuthCardCheckboxInput,
  AuthCardContainer,
  AuthCardPasswordInput,
  AuthCardTextInput,
} from "./utils";

type LoginUserProps = {
  csrf_token: string;
  initial_form_data: any;
  initial_errors: any;
};

function LoginUser({
  csrf_token,
  initial_form_data,
  initial_errors,
}: LoginUserProps): JSX.Element {
  const { t } = useTranslation();

  return (
    <AuthCardContainer>
      <div className="auth-card-container">
        <div className="auth-card">
          <h2 className="page-title text-center">{t("Welcome back!")}</h2>
          <Formik
            initialValues={{
              username: initial_form_data.username ?? "",
              password: initial_form_data.password ?? "",
              remember_me: "true",
              csrf_token,
            }}
            initialErrors={initial_errors}
            initialTouched={initial_errors}
            validationSchema={Yup.object({
              username: Yup.string().required(t("Username is required!")),
              password: Yup.string().required(t("Password is required!")),
            })}
            onSubmit={() => {}}
          >
            {({ errors }) => (
              <form method="POST">
                <AuthCardTextInput
                  label={t("Username")}
                  labelLink={
                    <a className="form-label-link small" href="/lost-username">
                      {t("Forgot username?")}
                    </a>
                  }
                  type="text"
                  name="username"
                  id="username"
                  required
                />

                <AuthCardPasswordInput
                  label={t("Password")}
                  labelLink={
                    <a className="form-label-link small" href="/lost-password">
                      {t("Forgot password?")}
                    </a>
                  }
                  name="password"
                  id="password"
                  required
                />

                <small className="checkbox">
                  <AuthCardCheckboxInput
                    label={t("Remember me")}
                    id="remember_me"
                    name="remember_me"
                    type="checkbox"
                  />
                </small>

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

                <button
                  className="btn btn-primary btn-block main-action-button"
                  type="submit"
                >
                  {t("Sign in")}
                </button>
              </form>
            )}
          </Formik>
          <div className="auth-card-footer text-center">
            {t("Don't have an account?")} <a href="/signup">{t("Sign up")}</a>
          </div>
        </div>
      </div>
    </AuthCardContainer>
  );
}

document.addEventListener("DOMContentLoaded", () => {
  const { domContainer, reactProps } = getPageProps();
  const { csrf_token, initial_form_data, initial_errors } = reactProps;

  renderRoot(
    domContainer!,
    <LoginUser
      csrf_token={csrf_token}
      initial_form_data={initial_form_data}
      initial_errors={initial_errors}
    />
  );
});
