import { Formik } from "formik";
import React, { JSX } from "react";
import { useTranslation } from "react-i18next";
import * as Yup from "yup";
import MTCaptcha from "./MTCaptcha";
import { getPageProps, renderRoot } from "../utils";
import {
  AuthCardContainer,
  AuthCardCheckboxInput,
  AuthCardPasswordInput,
  AuthCardTextInput,
  FormLevelAlert,
} from "./utils";
import ConditionsModal from "./ConditionsModal";
import useEmailValidation from "../hooks/useEmailValidation";

type SignupUserProps = {
  mtcaptcha_site_key: string;
  csrf_token: string;
  initial_form_data: any;
  initial_errors: any;
};

function SignupUser({
  csrf_token,
  mtcaptcha_site_key,
  initial_form_data,
  initial_errors,
}: SignupUserProps): JSX.Element {
  const { t } = useTranslation();
  const { isValidatingEmail, validateEmailAsync } = useEmailValidation();

  return (
    <AuthCardContainer>
      <div className="auth-card-container">
        <div className="auth-card">
          <h2 className="page-title text-center">
            {t("Create your account")}
          </h2>
          <div className="h4 text-center">
            {t("access all MetaBrainz projects")}
          </div>
          <Formik
            initialValues={{
              username: initial_form_data.username ?? "",
              email: initial_form_data.email ?? "",
              password: initial_form_data.password ?? "",
              confirm_password: initial_form_data.confirm_password ?? "",
              agreement: initial_form_data.agreement ?? false,
              mtcaptcha: "",
              csrf_token,
            }}
            initialErrors={initial_errors}
            initialTouched={initial_errors}
            validationSchema={Yup.object({
              username: Yup.string().required(t("Username is required!")),
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
              agreement: Yup.boolean()
                .required(t("You need to accept the agreement!"))
                .oneOf([true], t("You need to accept the agreement!")),
              mtcaptcha: mtcaptcha_site_key
                ? Yup.string().required(t("Captcha is required!"))
                : Yup.string(),
            })}
            onSubmit={() => {}}
          >
            {({ errors, isValid, dirty }) => (
              <form method="POST">
                <FormLevelAlert errors={initial_errors} />
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

                <AuthCardTextInput
                  label={
                    <>
                      {t("Username")} <span className="small">{t("(public)")}</span>
                    </>
                  }
                  type="text"
                  name="username"
                  id="username"
                  required
                />

                <AuthCardTextInput
                  label={
                    <>
                      {t("E-mail address")}
                      {isValidatingEmail && (
                        <span className="small text-muted">
                          {" "}
                          {t("(checking...)")}
                        </span>
                      )}
                    </>
                  }
                  type="email"
                  name="email"
                  id="email"
                  required
                  validate={validateEmailAsync}
                />

                <AuthCardPasswordInput
                  label={t("Password")}
                  name="password"
                  id="password"
                  required
                  labelLink={
                    <div className="small text-muted form-label-link">
                      {t("Must be at least 8 characters")}
                    </div>
                  }
                />

                <AuthCardPasswordInput
                  label={t("Confirm Password")}
                  name="confirm_password"
                  id="confirm_password"
                  required
                />

                <AuthCardCheckboxInput
                  id="agreement"
                  name="agreement"
                  type="checkbox"
                  required
                  label={
                  <span style={{ marginLeft: "0.5rem", fontWeight: "normal" }}>
                      {t(
                        "I accept that my contributions will be released into the public domain or licensed for use."
                      )}{" "}
                    </span>
                  }
                  />

                <div className="text-center" style={{ fontSize: "1.3rem" }}>
                  <b>
                    {t("We will never share your personal information.")}
                  </b>
                  <button
                    className="btn btn-link"
                    type="button"
                    role="link"
                    data-toggle="modal"
                    data-target="#conditions-modal"
                  >
                    {t("Click here to read more")}
                  </button>
                </div>

                {mtcaptcha_site_key && (
                  <div
                    className="main-action-button"
                    style={{
                      width: "fit-content",
                    }}
                  >
                    <MTCaptcha
                      sitekey={mtcaptcha_site_key}
                      size="compact"
                      fieldName="mtcaptcha"
                    />
                  </div>
                )}

                <button
                  className="btn btn-primary btn-block main-action-button"
                  type="submit"
                  disabled={!isValid || !dirty || isValidatingEmail}
                >
                  {isValidatingEmail ? t("Validating...") : t("Create account")}
                </button>
              </form>
            )}
          </Formik>
          <ConditionsModal />
          <div className="auth-card-footer text-center">
            {t("Already have an account?")} <a href="/login">{t("Sign in")}</a>
          </div>
        </div>
      </div>
    </AuthCardContainer>
  );
}

document.addEventListener("DOMContentLoaded", () => {
  const { domContainer, reactProps } = getPageProps();
  const { mtcaptcha_site_key, csrf_token, initial_form_data, initial_errors } =
    reactProps;

  renderRoot(
    domContainer!,
    <SignupUser
      mtcaptcha_site_key={mtcaptcha_site_key}
      csrf_token={csrf_token}
      initial_form_data={initial_form_data}
      initial_errors={initial_errors}
    />
  );
});
