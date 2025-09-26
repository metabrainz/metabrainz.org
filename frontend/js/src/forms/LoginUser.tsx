import { Formik } from "formik";
import React, { JSX } from "react";
import { createRoot } from "react-dom/client";
import * as Yup from "yup";
import { getPageProps } from "../utils";
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
  return (
    <AuthCardContainer>
      <div className="auth-card-container">
        <div className="auth-card">
          <h2 className="page-title text-center">Welcome back!</h2>
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

                <AuthCardTextInput
                  label={
                    <>
                      Username{" "}
                      <span
                        className="small"
                        style={{ display: "inline-block", color: "#404040" }}
                      >
                        (public)
                      </span>
                    </>
                  }
                  type="text"
                  name="username"
                  id="username"
                  required
                >
                  <a className="form-label-link small" href="/lost-username">
                    Forgot username?
                  </a>
                </AuthCardTextInput>

                <AuthCardPasswordInput
                  label="Password"
                  name="password"
                  id="password"
                  required
                >
                  <a className="form-label-link small" href="/lost-password">
                    Forgot password?
                  </a>
                </AuthCardPasswordInput>

                <small className="checkbox">
                  <AuthCardCheckboxInput
                    label="Remember me"
                    id="remember_me"
                    name="remember_me"
                    type="checkbox"
                  />
                </small>

                <button
                  className="btn btn-primary main-action-button"
                  type="submit"
                >
                  Sign in
                </button>
              </form>
            )}
          </Formik>
          <div className="auth-card-footer text-center">
            Don&apos;t have an account? <a href="/signup">Sign up</a>
          </div>
        </div>
      </div>
    </AuthCardContainer>
  );
}

document.addEventListener("DOMContentLoaded", () => {
  const { domContainer, reactProps } = getPageProps();
  const { csrf_token, initial_form_data, initial_errors } = reactProps;

  const renderRoot = createRoot(domContainer!);
  renderRoot.render(
    <LoginUser
      csrf_token={csrf_token}
      initial_form_data={initial_form_data}
      initial_errors={initial_errors}
    />
  );
});
