import { Formik } from "formik";
import React, { JSX } from "react";
import { createRoot } from "react-dom/client";
import ReCAPTCHA from "react-google-recaptcha";
import * as Yup from "yup";
import { getPageProps } from "../utils";
import {
  CheckboxInput,
  Dataset,
  DatasetsInput,
  TextAreaInput,
  TextInput,
} from "./utils";

type SignupNonCommercialProps = {
  datasets: Dataset[];
  mb_username: string;
  recaptcha_site_key: string;
  csrf_token: string;
  initial_form_data: any;
  initial_errors: any;
};

function SignupNonCommercial({
  datasets,
  mb_username,
  csrf_token,
  recaptcha_site_key,
  initial_form_data,
  initial_errors,
}: SignupNonCommercialProps): JSX.Element {
  return (
    <>
      <h1 className="page-title">
        Sign up <small>non-commercial</small>
      </h1>
      <p>
        Please be aware that misuse of the non-commercial service for commercial
        purposes will result in us revoking your access token and then billing
        you for your commercial use of our datasets or the Live Data Feed.
      </p>

      <Formik
        initialValues={{
          datasets: [],
          usage_desc: initial_form_data.usage_desc ?? "",
          contact_name: initial_form_data.contact_name ?? "",
          contact_email: initial_form_data.contact_email ?? "",
          agreement: false,
          recaptcha: "",
          csrf_token,
        }}
        initialErrors={initial_errors}
        initialTouched={initial_errors}
        validationSchema={Yup.object({
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
                <div className="alert alert-danger">{errors.csrf_token}</div>
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

            <div className="form-group">
              <div className="col-sm-4 control-label">
                <strong>MusicBrainz Account</strong>
              </div>
              <div className="col-sm-5" style={{ paddingTop: "7px" }}>
                {mb_username}
              </div>
            </div>
            <hr />

            <TextInput
              type="text"
              id="contact_name"
              name="contact_name"
              label="Name"
              required
            />

            <TextInput
              type="email"
              id="contact_email"
              name="contact_email"
              label="Email"
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
                I agree to use the MetaBrainz data for non-commercial (less than
                $500 income per year) or personal uses only.
              </p>
              <p>
                I also agree that if I generate a Live Data Feed access token,
                then I will treat my access token as a secret and will not share
                this token publicly or commit it to a source code repository.
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
    </>
  );
}

document.addEventListener("DOMContentLoaded", () => {
  const { domContainer, reactProps, globalProps } = getPageProps();
  const {
    datasets,
    mb_username,
    recaptcha_site_key,
    csrf_token,
    initial_form_data,
    initial_errors,
  } = reactProps;

  const renderRoot = createRoot(domContainer!);
  renderRoot.render(
    <SignupNonCommercial
      datasets={datasets}
      mb_username={mb_username}
      recaptcha_site_key={recaptcha_site_key}
      csrf_token={csrf_token}
      initial_form_data={initial_form_data}
      initial_errors={initial_errors}
    />
  );
});
