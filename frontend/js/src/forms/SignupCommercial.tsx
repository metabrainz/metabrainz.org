import { Formik, useField, FieldConfig } from "formik";
import React, { JSX } from "react";
import { createRoot } from "react-dom/client";
import ReCAPTCHA from "react-google-recaptcha";
import * as Yup from "yup";
import { getPageProps } from "../utils";
import {
  AuthCardContainer,
  AuthCardTextInput,
  CheckboxInput,
  TextAreaInput,
} from "./utils";

type AmountPledgedFieldProps = JSX.IntrinsicElements["input"] &
  FieldConfig & {
    tier: {
      name: string;
      price: number;
    };
  };

function AmountPledgedField({ tier, ...props }: AmountPledgedFieldProps) {
  const [field, meta] = useField(props);
  return (
    <div className="form-group">
      <label className="col-sm-offset-4 col-sm-5" htmlFor="amount_pledged">
        If you would like to support us with more than ${tier.price}, please
        enter the actual amount here:
      </label>
      <div className="col-sm-offset-4 col-sm-5">
        <input
          step="any"
          className="form-control"
          min={tier.price}
          {...field}
          {...props}
        />
      </div>
      {meta.touched && meta.error ? (
        <div
          className="col-sm-offset-4 col-sm-5"
          style={{ paddingTop: "7px", color: "red" }}
        >
          {meta.error}
        </div>
      ) : null}
    </div>
  );
}

type SignupCommercialProps = {
  tier: {
    name: string;
    price: number;
  };
  recaptcha_site_key: string;
  csrf_token: string;
  initial_form_data: any;
  initial_errors: any;
};

function SignupCommercial({
  tier,
  csrf_token,
  recaptcha_site_key,
  initial_form_data,
  initial_errors,
}: SignupCommercialProps): JSX.Element {
  return (
    <AuthCardContainer>
      <div className="auth-card-container">
        <div className="auth-card">
          <h1 className="page-title text-center">
            Sign up <small>Commercial</small>
          </h1>
          <div className="h4 text-center">access all MetaBrainz projects</div>
          <p>
            <strong>Note:</strong> Signing up for any tier other than the{" "}
            <i>Stealth startup</i> tier will publicly list your company on this
            web site. However, we will not publish any of your private details.
          </p>

          <Formik
            initialValues={{
              username: initial_form_data.username ?? "",
              email: initial_form_data.email ?? "",
              password: initial_form_data.password ?? "",
              confirm_password: initial_form_data.confirm_password ?? "",
              org_name: initial_form_data.org_name ?? "",
              org_desc: initial_form_data.org_desc ?? "",
              website_url: initial_form_data.website_url ?? "",
              logo_url: initial_form_data.logo_url ?? "",
              api_url: initial_form_data.api_url ?? "",
              address_street: initial_form_data.address_street ?? "",
              address_city: initial_form_data.address_city ?? "",
              address_state: initial_form_data.address_state ?? "",
              address_postcode: initial_form_data.address_postcode ?? "",
              address_country: initial_form_data.address_country ?? "",
              amount_pledged: initial_form_data.amount_pledged ?? tier.price,
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
              org_name: Yup.string().required(
                "You need to specify the name of your organization."
              ),
              org_desc: Yup.string().required(
                "You need to provide description of your organization."
              ),
              website_url: Yup.string().required(
                "You need to specify website of the organization."
              ),
              logo_url: Yup.string(),
              api_url: Yup.string(),
              address_street: Yup.string().required(
                "You need to specify street."
              ),
              address_city: Yup.string().required("You need to specify city."),
              address_state: Yup.string().required(
                "You need to specify state/province."
              ),
              address_postcode: Yup.string().required(
                "You need to specify postcode."
              ),
              address_country: Yup.string().required(
                "You need to specify country."
              ),
              amount_pledged: Yup.number().min(
                tier.price,
                "Custom amount must be more than threshold amount for selected tier or equal to it!"
              ),
              usage_desc: Yup.string()
                .required("Please, tell us how you (will) use our data.")
                .max(500, "Please, limit usage description to 500 characters."),
              contact_name: Yup.string().required("Contact name is required!"),
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
                    Commercial
                  </div>
                  <div className="col-sm-4 control-label">
                    <strong>Selected tier</strong>
                  </div>
                  <div className="col-sm-5" style={{ paddingTop: "7px" }}>
                    <b>{tier.name}</b>
                    <em className="text-muted">${tier.price}/month and up</em>
                  </div>
                  <div
                    className="col-sm-6 col-sm-offset-4"
                    style={{ paddingTop: "7px" }}
                  >
                    <a href="/supporters/account-type">
                      Change account type or tier
                    </a>
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

                <AuthCardTextInput
                  type="text"
                  id="org_name"
                  name="org_name"
                  label="Organization name"
                  required
                >
                  <div
                    className="col-sm-offset-4 col-sm-5"
                    style={{ paddingTop: "7px" }}
                  >
                    <em className="text-muted">
                      If you don&apos;t have an organization name, you probably
                      want to sign up as a{" "}
                      <a href="/signup/noncommercial">
                        non-commercial / personal
                      </a>{" "}
                      user.
                    </em>
                  </div>
                </AuthCardTextInput>

                <TextAreaInput
                  id="org_desc"
                  name="org_desc"
                  label="Organization description"
                  required
                >
                  <div
                    className="col-sm-offset-4 col-sm-5"
                    style={{ paddingTop: "7px" }}
                  >
                    <em className="text-muted">
                      Please tell us a little about your company and whether you
                      plan to use our{" "}
                      <a href="https://musicbrainz.org/doc/Development/XML_Web_Service/Version_2">
                        API
                      </a>
                      or to{" "}
                      <a href="https://musicbrainz.org/doc/MusicBrainz_Server/Setup">
                        host your own copy
                      </a>{" "}
                      of the data.
                    </em>
                  </div>
                </TextAreaInput>

                <AuthCardTextInput
                  type="text"
                  id="website_url"
                  name="website_url"
                  label="Website URL"
                  required
                />

                <AuthCardTextInput
                  type="text"
                  id="logo_url"
                  name="logo_url"
                  label="Logo URL"
                  placeholder="(preferably in SVG format)"
                >
                  <div
                    className="col-sm-offset-4 col-sm-5"
                    style={{ paddingTop: "7px" }}
                  >
                    <em className="text-muted">
                      Image should be about 250 pixels wide on a white or
                      transparent background. We will host it on our site.
                    </em>
                  </div>
                </AuthCardTextInput>

                <AuthCardTextInput
                  type="text"
                  id="api_url"
                  name="api_url"
                  label="API URL"
                >
                  <div
                    className="col-sm-offset-4 col-sm-5"
                    style={{ paddingTop: "7px" }}
                  >
                    <em className="text-muted">
                      URL to where developers can use your APIs using
                      MusicBrainz IDs, if available..
                    </em>
                  </div>
                </AuthCardTextInput>

                <TextAreaInput
                  id="usage_desc"
                  name="usage_desc"
                  label="Can you please tell us more about the project in which you'd like to use our data? Do you plan to self host the data or use our APIs?"
                  maxLength={150}
                  required
                  placeholder="(max 150 characters)"
                />
                <br />

                <AmountPledgedField
                  id="amount_pledged"
                  name="amount_pledged"
                  type="number"
                  tier={tier}
                />
                <br />

                <div className="form-group">
                  <div className="col-sm-offset-4 col-sm-5">
                    <strong>Billing address</strong>
                  </div>
                </div>

                <AuthCardTextInput
                  type="text"
                  id="address_street"
                  name="address_street"
                  label="Street"
                  required
                />

                <AuthCardTextInput
                  type="text"
                  id="address_city"
                  name="address_city"
                  label="City"
                  required
                />

                <AuthCardTextInput
                  type="text"
                  id="address_state"
                  name="address_state"
                  label="State / Province"
                  required
                />

                <AuthCardTextInput
                  type="text"
                  id="address_postcode"
                  name="address_postcode"
                  label="Postcode"
                  required
                />

                <AuthCardTextInput
                  type="text"
                  id="address_country"
                  name="address_country"
                  label="Country"
                  required
                />
                <br />
                <hr />

                <CheckboxInput
                  label=""
                  id="agreement"
                  name="agreement"
                  type="checkbox"
                  required
                >
                  <p>
                    I agree to support the MetaBrainz Foundation when my
                    organization is able to do so.
                  </p>
                  <p>
                    I also agree that if I generate a Live Data Feed access
                    token, that I treat my access token as a secret and will not
                    share this token publicly or commit it to a source code
                    repository.
                  </p>
                </CheckboxInput>

                <div className="col-sm-offset-4 col-sm-8 small">
                  <em>
                    The following information will be shown publicly:
                    organization name, logo, website and API URLs, data usage
                    description.
                    <br />
                  </em>
                </div>

                <div className="col-sm-offset-4 col-sm-8 small">
                  <em>
                    We&apos;ll send you more details about payment process once
                    your application is approved.
                    <br />
                    <br />
                  </em>
                </div>

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
    tier,
    recaptcha_site_key,
    csrf_token,
    initial_form_data,
    initial_errors,
  } = reactProps;

  const renderRoot = createRoot(domContainer!);
  renderRoot.render(
    <SignupCommercial
      tier={tier}
      recaptcha_site_key={recaptcha_site_key}
      csrf_token={csrf_token}
      initial_form_data={initial_form_data}
      initial_errors={initial_errors}
    />
  );
});
