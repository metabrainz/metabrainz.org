import { Formik } from "formik";
import React, { JSX } from "react";
import { createRoot } from "react-dom/client";
import ReCAPTCHA from "react-google-recaptcha";
import * as Yup from "yup";
import { getPageProps } from "../utils";
import {
  AuthCardCheckboxInput,
  AuthCardContainer,
  AuthCardTextInput,
} from "./utils";

type LoginUserProps = {
  recaptcha_site_key: string;
  csrf_token: string;
  initial_form_data: any;
  initial_errors: any;
};

function LoginUser({
  csrf_token,
  recaptcha_site_key,
  initial_form_data,
  initial_errors,
}: LoginUserProps): JSX.Element {
  return (
    <AuthCardContainer>
      <div className="auth-card-container">
        <div className="auth-card">
          <h1 className="page-title text-center">Welcome back!</h1>
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
              username: Yup.string().required("Username is required!"),
              password: Yup.string().required("Password is required!"),
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
                        className="small help-block"
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
                  label="Password"
                  type="password"
                  name="password"
                  id="password"
                  required
                />

                <div className="auth-card-bottom">
                  <small className="checkbox">
                    <AuthCardCheckboxInput
                      label="Remember me"
                      id="remember_me"
                      name="remember_me"
                      type="checkbox"
                    />
                  </small>
                  <small>
                    I forgot my <a href="/lost-username">username</a> /{" "}
                    <a href="/lost-password">password</a>
                  </small>
                </div>

                <button
                  className="btn btn-primary main-action-button"
                  type="submit"
                >
                  Sign in
                </button>
              </form>
            )}
          </Formik>
          <div className="auth-card-footer">
            <div className="small">
              Don‘t have an account?
              <a href={`/signup${window.location.search}`}>
                {" "}
                Create a free MetaBrainz account{" "}
              </a>
              to access MusicBrainz, ListenBrainz, CritiqueBrainz, and more.
            </div>
          </div>
        </div>
      </div>
    </AuthCardContainer>
  );
}

document.addEventListener("DOMContentLoaded", () => {
  const { domContainer, reactProps, globalProps } = getPageProps();
  const { recaptcha_site_key, csrf_token, initial_form_data, initial_errors } =
    reactProps;

  const renderRoot = createRoot(domContainer!);
  renderRoot.render(
    <LoginUser
      recaptcha_site_key={recaptcha_site_key}
      csrf_token={csrf_token}
      initial_form_data={initial_form_data}
      initial_errors={initial_errors}
    />
  );
});
