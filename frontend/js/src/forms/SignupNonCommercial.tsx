import { Formik } from "formik";
import React, { JSX } from "react";
import { useTranslation } from "react-i18next";
import * as Yup from "yup";
import MTCaptcha from "./MTCaptcha";
import { getPageProps, renderRoot } from "../utils";
import {
  AuthCardContainer,
  AuthCardPasswordInput,
  AuthCardTextInput,
  CheckboxInput,
  DatasetsInput,
  FormLevelAlert,
  TextAreaInput,
} from "./utils";
import useEmailValidation from "../hooks/useEmailValidation";

type UserInfo = {
  username: string;
  email: string;
};

type SupporterNonCommercialProps = {
  datasets: Dataset[];
  user?: UserInfo;
  mtcaptcha_site_key: string;
  csrf_token: string;
  initial_form_data: any;
  initial_errors: any;
  existing_user: boolean;
};

function SignupNonCommercial({
  datasets,
  user,
  csrf_token,
  mtcaptcha_site_key,
  initial_form_data,
  initial_errors,
  existing_user,
}: SupporterNonCommercialProps): JSX.Element {
  const { t } = useTranslation();
  const accountTypeUrl = "/supporters/account-type";
  const { isValidatingEmail, validateEmailAsync } = useEmailValidation();

  const baseInitialValues = {
    datasets: [],
    usage_desc: initial_form_data.usage_desc ?? "",
    contact_name: initial_form_data.contact_name ?? "",
    agreement: false,
    mtcaptcha: "",
    csrf_token,
  };

  const initialValues = existing_user
    ? baseInitialValues
    : {
        ...baseInitialValues,
        username: initial_form_data.username ?? "",
        email: initial_form_data.email ?? "",
        password: initial_form_data.password ?? "",
        confirm_password: initial_form_data.confirm_password ?? "",
      };

  // Build validation schema based on whether it's signup or upgrade
  const baseValidationSchema = {
    usage_desc: Yup.string()
      .required(t("Please, tell us how you (will) use our data."))
      .max(500, t("Please, limit usage description to 500 characters.")),
    contact_name: Yup.string().required(t("Contact name is required!")),
    agreement: Yup.boolean()
      .required(t("You need to accept the agreement!"))
      .oneOf([true], t("You need to accept the agreement!")),
    mtcaptcha: mtcaptcha_site_key
      ? Yup.string().required(t("Captcha is required!"))
      : Yup.string(),
  };

  const validationSchema = Yup.object(
    existing_user
      ? baseValidationSchema
      : {
          ...baseValidationSchema,
          username: Yup.string().required(t("Username is required!")),
          email: Yup.string().email().required(t("Email address is required!")),
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
        }
  );

  return (
    <AuthCardContainer>
      <div className="auth-card-container">
        <div className="auth-card">
          <h1 className="page-title text-center">
            {existing_user ? t("Become a Supporter") : t("Sign up")}{" "}
            <small>{t("Non-commercial")}</small>
          </h1>
          <div className="h4 text-center">
            {t("Access all MetaBrainz projects")}
          </div>
          <p>
            {t(
              "Please be aware that misuse of the non-commercial service for commercial purposes will result in us revoking your access token and then billing you for your commercial use of our datasets or the Live Data Feed."
            )}
          </p>
          <Formik
            initialValues={initialValues}
            initialErrors={initial_errors}
            initialTouched={initial_errors}
            validationSchema={validationSchema}
            onSubmit={() => {}}
          >
            {({ errors, isValid, dirty }) => (
              <form method="POST" className="d-flex flex-column">
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
                <div className="form-horizontal">
                  <div className="form-group">
                    <div className="col-sm- col-xs-6 control-label">
                      <strong>{t("Account type")}</strong>
                    </div>
                    <div
                      className="col-sm-5 col-xs-6 label label-success"
                      style={{ padding: "10px" }}
                    >
                      {t("Non-commercial")}
                    </div>
                    <div
                      className="btn btn-link col-sm-offset-4 col-xs-offset-5"
                      style={{ marginTop: "10px" }}
                    >
                      <a href={accountTypeUrl}>{t("Change account type")}</a>
                    </div>
                  </div>
                </div>
                <hr />

                {existing_user && user ? (
                  <div className="form-group">
                    <div className="alert alert-info">
                      <strong>{t("Your account:")}</strong> {user.username} (
                      {user.email})
                    </div>
                  </div>
                ) : (
                  <>
                    <AuthCardTextInput
                      label={
                        <>
                          {t("Username")}{" "}
                          <span className="small">{t("(public)")}</span>
                        </>
                      }
                      type="text"
                      name="username"
                      id="username"
                      required
                    />

                    <AuthCardTextInput
                      type="text"
                      id="contact_name"
                      name="contact_name"
                      label={t("Contact name")}
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
                      autoComplete="email"
                      required
                      validate={validateEmailAsync}
                    />

                    <AuthCardPasswordInput
                      label={t("Password")}
                      name="password"
                      id="password"
                      autoComplete="new-password"
                      labelLink={
                        <div className="small text-muted form-label-link">
                          {t("Must be at least 8 characters")}
                        </div>
                      }
                      required
                    />

                    <AuthCardPasswordInput
                      label={t("Confirm Password")}
                      name="confirm_password"
                      id="confirm_password"
                      autoComplete="new-password"
                      required
                    />
                  </>
                )}

                {existing_user && (
                  <AuthCardTextInput
                    type="text"
                    id="contact_name"
                    name="contact_name"
                    label={t("Contact name")}
                    required
                  />
                )}
                <br />

                <div className="form-group">
                  <label htmlFor="datasets">
                    {t("Which datasets are you interested in?")}
                  </label>
                  <DatasetsInput datasets={datasets} />
                </div>

                <TextAreaInput
                  id="usage_desc"
                  name="usage_desc"
                  label={t("About your project")}
                  maxLength={150}
                  rows={6}
                  required
                  placeholder={t("(max 150 characters)")}
                >
                  <p>
                    {t(
                      "Can you please tell us more about the project in which you'd like to use our data? Do you plan to self host the data or use our APIs?"
                    )}
                  </p>
                </TextAreaInput>
                <hr />

                <CheckboxInput
                  label=""
                  id="agreement"
                  name="agreement"
                  type="checkbox"
                  required
                >
                  <p>
                    {t(
                      "I agree to use the MetaBrainz data for non-commercial (less than $500 income per year) or personal uses only."
                    )}
                  </p>
                  <p>
                    {t(
                      "I also agree that if I generate a Live Data Feed access token, then I will treat my access token as a secret and will not share this token publicly or commit it to a source code repository."
                    )}
                  </p>
                </CheckboxInput>

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

                <div className="form-group main-action-button">
                  <button
                    type="submit"
                    className="btn btn-primary btn-block"
                    disabled={
                      !isValid ||
                      !dirty ||
                      (!existing_user && isValidatingEmail)
                    }
                  >
                    {!existing_user && isValidatingEmail
                      ? t("Validating...")
                      : existing_user
                      ? t("Become a Supporter")
                      : t("Sign up")}
                  </button>
                </div>
                <br />
              </form>
            )}
          </Formik>
          <div className="auth-card-footer">
            {existing_user ? (
              <div className="small">
                <a href="/profile">{t("Back to profile")}</a>
              </div>
            ) : (
              <>
                <div className="small">
                  {t("Not a supporter?")}{" "}
                  <a href="/signup">{t("Create a user account")}</a>
                </div>
                <div className="small">
                  {t("Already have an account?")}{" "}
                  <a href="/login">{t("Sign in")}</a>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </AuthCardContainer>
  );
}

document.addEventListener("DOMContentLoaded", () => {
  const { domContainer, reactProps } = getPageProps();
  const {
    datasets,
    user,
    mtcaptcha_site_key,
    csrf_token,
    initial_form_data,
    initial_errors,
    existing_user,
  } = reactProps;

  renderRoot(
    domContainer!,
    <SignupNonCommercial
      datasets={datasets}
      user={user}
      mtcaptcha_site_key={mtcaptcha_site_key}
      csrf_token={csrf_token}
      initial_form_data={initial_form_data}
      initial_errors={initial_errors}
      existing_user={existing_user}
    />
  );
});
