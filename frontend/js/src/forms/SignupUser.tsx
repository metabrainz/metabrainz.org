import { Formik } from "formik";
import React, { JSX } from "react";
import { createRoot } from "react-dom/client";
import ReCAPTCHA from "react-google-recaptcha";
import * as Yup from "yup";
import { getPageProps } from "../utils";
import { AuthCardContainer, AuthCardTextInput } from "./utils";
import ConditionsModal from "./ConditionsModal";

type SignupUserProps = {
  recaptcha_site_key: string;
  csrf_token: string;
  initial_form_data: any;
  initial_errors: any;
};

function SignupUser({
  csrf_token,
  recaptcha_site_key,
  initial_form_data,
  initial_errors,
}: SignupUserProps): JSX.Element {
  return (
    <AuthCardContainer>
      <div className="auth-card-container">
        <div className="auth-card">
          <h2 className="page-title text-center">Create your account</h2>
          <div className="h4 text-center">access all MetaBrainz projects</div>
          <Formik
            initialValues={{
              username: initial_form_data.username ?? "",
              email: initial_form_data.email ?? "",
              password: initial_form_data.password ?? "",
              confirm_password: initial_form_data.confirm_password ?? "",
              recaptcha: "",
              csrf_token,
            }}
            initialErrors={initial_errors}
            initialTouched={initial_errors}
            validationSchema={Yup.object({
              username: Yup.string().required("Username is required!"),
              email: Yup.string()
                .email()
                .required("Email address is required!"),
              password: Yup.string()
                .required("Password is required!")
                .min(8)
                .max(64),
              confirm_password: Yup.string()
                .required()
                .min(8)
                .max(64)
                .oneOf(
                  [Yup.ref("password")],
                  "Confirm Password should match password!"
                ),
              recaptcha: Yup.string().required(),
            })}
            onSubmit={() => {}}
          >
            {({ errors, setFieldValue }) => (
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

                <AuthCardTextInput
                  label={
                    <>
                      Username{" "}
                      <span
                        className="small"
                        style={{ display: "inline-block" }}
                      >
                        (public)
                      </span>
                    </>
                  }
                  type="text"
                  name="username"
                  id="username"
                  required
                />

                <AuthCardTextInput
                  label="E-mail address"
                  type="email"
                  name="email"
                  id="email"
                  required
                />

                <AuthCardTextInput
                  label="Password"
                  type="password"
                  name="password"
                  id="password"
                  required
                />

                <AuthCardTextInput
                  label="Confirm Password"
                  type="password"
                  name="confirm_password"
                  id="confirm_password"
                  required
                />

                <div className="form-group">
                  <ReCAPTCHA
                    sitekey={recaptcha_site_key}
                    onChange={(value) => setFieldValue("recaptcha", value)}
                  />
                </div>

                <div className="small" style={{ fontSize: "1.3rem" }}>
                  Please note that your contributions will be released into the
                  public domain or licensed for use. We will never share your
                  personal information.
                  <br />
                  <button
                    className="small btn-link"
                    type="button"
                    role="link"
                    data-toggle="modal"
                    data-target="#conditions-modal"
                  >
                    Click here to read more
                  </button>
                </div>

                <button
                  className="btn btn-primary main-action-button"
                  type="submit"
                >
                  Create account
                </button>
              </form>
            )}
          </Formik>
          <ConditionsModal />
          <div className="auth-card-footer text-center">
            Already have an account? <a href="/login">Sign in </a>
          </div>
        </div>
      </div>
    </AuthCardContainer>
  );
}

document.addEventListener("DOMContentLoaded", () => {
  const { domContainer, reactProps } = getPageProps();
  const { recaptcha_site_key, csrf_token, initial_form_data, initial_errors } =
    reactProps;

  const renderRoot = createRoot(domContainer!);
  renderRoot.render(
    <SignupUser
      recaptcha_site_key={recaptcha_site_key}
      csrf_token={csrf_token}
      initial_form_data={initial_form_data}
      initial_errors={initial_errors}
    />
  );
});
