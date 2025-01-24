import { Formik } from "formik";
import React, { JSX } from "react";
import { createRoot } from "react-dom/client";
import * as Yup from "yup";
import { getPageProps } from "../utils";
import { AuthCardContainer, AuthCardTextInput } from "./utils";

type LostUsernameProps = {
  csrf_token: string;
  initial_form_data: any;
  initial_errors: any;
};

function LostUsername({
  csrf_token,
  initial_form_data,
  initial_errors,
}: LostUsernameProps): JSX.Element {
  return (
    <AuthCardContainer>
      <div className="auth-card-container">
        <div className="auth-card">
          <h1 className="page-title text-center">Forgot your username?</h1>
          <Formik
            initialValues={{
              email: initial_form_data.email ?? "",
              csrf_token,
            }}
            initialErrors={initial_errors}
            initialTouched={initial_errors}
            validationSchema={Yup.object({
              email: Yup.string().email().required("Email is required!"),
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
                  label="Email"
                  type="email"
                  name="email"
                  id="email"
                  required
                />

                <button
                  className="btn btn-primary main-action-button"
                  type="submit"
                >
                  Send Email
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
  const { csrf_token, initial_form_data, initial_errors } = reactProps;

  const renderRoot = createRoot(domContainer!);
  renderRoot.render(
    <LostUsername
      csrf_token={csrf_token}
      initial_form_data={initial_form_data}
      initial_errors={initial_errors}
    />
  );
});