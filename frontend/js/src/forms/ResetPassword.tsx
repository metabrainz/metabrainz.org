import { Formik } from "formik";
import React, { JSX } from "react";
import { createRoot } from "react-dom/client";
import * as Yup from "yup";
import { getPageProps } from "../utils";
import { AuthCardContainer, AuthCardTextInput } from "./utils";

type ResetPasswordProps = {
  csrf_token: string;
  initial_errors: any;
};

function ResetPassword({
  csrf_token,
  initial_errors,
}: ResetPasswordProps): JSX.Element {
  return (
    <AuthCardContainer>
      <div className="auth-card-container">
        <div className="auth-card">
          <h1 className="page-title text-center">Reset your password</h1>
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

                <button
                  className="btn btn-primary main-action-button"
                  type="submit"
                >
                  Reset Password
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
  const { domContainer, reactProps, globalProps } = getPageProps();
  const { csrf_token, initial_errors } = reactProps;

  const renderRoot = createRoot(domContainer!);
  renderRoot.render(
    <ResetPassword csrf_token={csrf_token} initial_errors={initial_errors} />
  );
});
