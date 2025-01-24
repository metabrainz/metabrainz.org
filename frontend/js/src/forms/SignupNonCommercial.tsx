import { Formik } from "formik";
import React, { JSX } from "react";
import { createRoot } from "react-dom/client";
import ReCAPTCHA from "react-google-recaptcha";
import * as Yup from "yup";
import { getPageProps } from "../utils";
import {
  AuthCardContainer,
  AuthCardTextInput,
  CheckboxInput,
  DatasetsInput,
  TextAreaInput,
} from "./utils";

type SignupNonCommercialProps = {
  datasets: Dataset[];
  recaptcha_site_key: string;
  csrf_token: string;
  initial_form_data: any;
  initial_errors: any;
};

function SignupNonCommercial({
  datasets,
  csrf_token,
  recaptcha_site_key,
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
              usage_desc: Yup.string()
                .required("Please, tell us how you (will) use our data.")
                .max(500, "Please, limit usage description to 500 characters."),
              contact_name: Yup.string().required("Contact name is required!"),
              contact_email: Yup.string()
                .email()
                .required("Email address is required!"),
              agreement: Yup.boolean()
                .required("You need to accept the agreement!")
                .oneOf([true], "You need to accept the agreement!"),
              recaptcha: Yup.string().required(),
            })}
            onSubmit={() => {}}
          >
            {({ errors, setFieldValue }) => (
              <form method="POST" className="form-horizontal">
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

                <div className="form-group">
                  <div className="col-sm-4 control-label">
                    <strong>Account type</strong>
                  </div>
                  <div className="col-sm-5" style={{ paddingTop: "7px" }}>
                    Non-commercial
                  </div>
                  <div
                    className="col-sm-6 col-sm-offset-4"
                    style={{ paddingTop: "7px" }}
                  >
                    <a href="/supporters/account-type">Change account type</a>
                  </div>
                </div>
                <hr />

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
                <br />

                <DatasetsInput datasets={datasets} />

                <TextAreaInput
                  id="usage_desc"
                  name="usage_desc"
                  label="Can you please tell us more about the project in which you'd like to use our data? Do you plan to self host the data or use our APIs?"
                  maxLength={150}
                  required
                  placeholder="(max 150 characters)"
                />
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

                <div className="form-group">
                  <div className="col-sm-offset-4 col-sm-8">
                    <ReCAPTCHA
                      sitekey={recaptcha_site_key}
                      onChange={(value) => setFieldValue("recaptcha", value)}
                    />
                  </div>
                </div>

                <div className="form-group">
                  <div className="col-sm-offset-4 col-sm-8">
                    <button type="submit" className="btn btn-primary">
                      Sign up
                    </button>
                  </div>
                </div>
                <br />
              </form>
            )}
          </Formik>
          <div className="modal fade" id="conditions-modal">
            <div className="modal-dialog" role="document">
              <div className="modal-content">
                <p>
                  Note that any contributions you make to MusicBrainz will be
                  released into the Public Domain and/or licensed under a
                  Creative Commons by-nc-sa license. Furthermore, you give the
                  MetaBrainz Foundation the right to license this data for
                  commercial use.
                  <br />
                  Please read our <a href="/social-contract">
                    {" "}
                    license page
                  </a>{" "}
                  for more details.
                </p>
                <p>
                  MusicBrainz believes strongly in the privacy of its users. Any
                  personal information you choose to provide will not be sold or
                  shared with anyone else.
                  <br />
                  Please read our <a href="/privacy">privacy policy</a> for more
                  details.
                </p>
                <p>
                  You may remove your personal information from our services
                  anytime by deleting your account.
                  <br />
                  Please read our <a href="/gdpr">
                    GDPR compliance statement
                  </a>{" "}
                  for more details.
                </p>
                <p>
                  Creating an account on MetaBrainz will give you access to
                  accounts on our other services, such as ListenBrainz,
                  MusicBrainz, BookBrainz, and more.
                  <br />
                  We do not automatically create accounts for these services
                  when you create a MetaBrainz account, but you will only be a
                  few clicks away doing so.
                </p>
                <button
                  className="btn btn-primary center-block"
                  type="button"
                  data-dismiss="modal"
                >
                  Sounds good
                </button>
              </div>
            </div>
          </div>
          <div className="auth-card-footer">
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
    recaptcha_site_key,
    csrf_token,
    initial_form_data,
    initial_errors,
  } = reactProps;

  const renderRoot = createRoot(domContainer!);
  renderRoot.render(
    <SignupNonCommercial
      datasets={datasets}
      recaptcha_site_key={recaptcha_site_key}
      csrf_token={csrf_token}
      initial_form_data={initial_form_data}
      initial_errors={initial_errors}
    />
  );
});
