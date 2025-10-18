import { Formik } from "formik";
import React, { JSX } from "react";
import { createRoot } from "react-dom/client";
import * as Yup from "yup";
import MTCaptcha from "./MTCaptcha";
import { getPageProps } from "../utils";
import {
  AuthCardContainer,
  AuthCardPasswordInput,
  AuthCardTextInput,
  CheckboxInput,
  DatasetsInput,
  TextAreaInput,
} from "./utils";

type SignupNonCommercialProps = {
  datasets: Dataset[];
  mtcaptcha_site_key: string;
  csrf_token: string;
  initial_form_data: any;
  initial_errors: any;
};

function SignupNonCommercial({
  datasets,
  csrf_token,
  mtcaptcha_site_key,
  initial_form_data,
  initial_errors,
}: SignupNonCommercialProps): JSX.Element {
  return (
    <AuthCardContainer>
      <div className="auth-card-container">
        <div className="auth-card">
          <h1 className="page-title text-center">
            Sign up <small>non-commercial</small>
          </h1>
          <div className="h4 text-center">access all MetaBrainz projects</div>
          <p>
            Please be aware that misuse of the non-commercial service for
            commercial purposes will result in us revoking your access token and
            then billing you for your commercial use of our datasets or the Live
            Data Feed.
          </p>
          <Formik
            initialValues={{
              username: initial_form_data.username ?? "",
              email: initial_form_data.email ?? "",
              password: initial_form_data.password ?? "",
              confirm_password: initial_form_data.confirm_password ?? "",
              datasets: [],
              usage_desc: initial_form_data.usage_desc ?? "",
              contact_name: initial_form_data.contact_name ?? "",
              agreement: false,
              mtcaptcha: "",
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
              usage_desc: Yup.string()
                .required("Please, tell us how you (will) use our data.")
                .max(500, "Please, limit usage description to 500 characters."),
              contact_name: Yup.string().required("Contact name is required!"),
              agreement: Yup.boolean()
                .required("You need to accept the agreement!")
                .oneOf([true], "You need to accept the agreement!"),
              mtcaptcha: Yup.string().required(),
            })}
            onSubmit={() => {}}
          >
            {({ errors, isValid, dirty }) => (
              <form method="POST" className="d-flex flex-column">
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
                      <strong>Account type</strong>
                    </div>
                    <div
                      className="col-sm-5 col-xs-6 label label-success"
                      style={{ padding: "10px" }}
                    >
                      Non-commercial
                    </div>
                    <div
                      className="btn btn-link col-sm-offset-4 col-xs-offset-5"
                      style={{ marginTop: "10px" }}
                    >
                      <a href="/supporters/account-type">Change account type</a>
                    </div>
                  </div>
                </div>
                <hr />

                <AuthCardTextInput
                  label={
                    <>
                      Username <span className="small">(public)</span>
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
                  label="Contact Name"
                  required
                />

                <AuthCardTextInput
                  label="E-mail address"
                  type="email"
                  name="email"
                  id="email"
                  autoComplete="email"
                  required
                />

                <AuthCardPasswordInput
                  label="Password"
                  name="password"
                  id="password"
                  autoComplete="new-password"
                  labelLink={
                    <div className="small text-muted form-label-link">
                      Must be at least 8 characters
                    </div>
                  }
                  required
                />

                <AuthCardPasswordInput
                  label="Confirm Password"
                  name="confirm_password"
                  id="confirm_password"
                  autoComplete="new-password"
                  required
                />
                <br />

                <div className="form-group">
                  <label htmlFor="datasets">
                    Which datasets are you interested in?
                  </label>
                  <DatasetsInput datasets={datasets} />
                </div>

                <TextAreaInput
                  id="usage_desc"
                  name="usage_desc"
                  label="About your project"
                  maxLength={150}
                  rows={6}
                  required
                  placeholder="(max 150 characters)"
                >
                  <p>
                    Can you please tell us more about the project in which
                    you&apos;d like to use our data? Do you plan to self host
                    the data or use our APIs?
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
                    I agree to use the MetaBrainz data for non-commercial (less
                    than $500 income per year) or personal uses only.
                  </p>
                  <p>
                    I also agree that if I generate a Live Data Feed access
                    token, then I will treat my access token as a secret and
                    will not share this token publicly or commit it to a source
                    code repository.
                  </p>
                </CheckboxInput>

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

                <div className="form-group main-action-button">
                  <button
                    type="submit"
                    className="btn btn-primary btn-block"
                    disabled={!isValid || !dirty}
                  >
                    Sign up
                  </button>
                </div>
                <br />
              </form>
            )}
          </Formik>
          <div className="auth-card-footer">
            <div className="small">
              Not a supporter? <a href="/signup">Create a user account </a>
            </div>
            <div className="small">
              Already have an account? <a href="/login">Sign in </a>
            </div>
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
    mtcaptcha_site_key,
    csrf_token,
    initial_form_data,
    initial_errors,
  } = reactProps;

  const renderRoot = createRoot(domContainer!);
  renderRoot.render(
    <SignupNonCommercial
      datasets={datasets}
      mtcaptcha_site_key={mtcaptcha_site_key}
      csrf_token={csrf_token}
      initial_form_data={initial_form_data}
      initial_errors={initial_errors}
    />
  );
});
