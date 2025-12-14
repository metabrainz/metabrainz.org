import { Formik, useField, FieldConfig } from "formik";
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
  TextAreaInput,
} from "./utils";

type TierInfo = {
  name: string;
  price: number;
};

type UserInfo = {
  username: string;
  email: string;
};

type AmountPledgedFieldProps = JSX.IntrinsicElements["input"] &
  FieldConfig & {
    tier: TierInfo;
  };

function AmountPledgedField({ tier, ...props }: AmountPledgedFieldProps) {
  const [field, meta] = useField(props);
  return (
    <div className="form-group">
      <label htmlFor="amount_pledged">
        If you would like to support us with more than ${tier.price}, please
        enter the actual amount here:
      </label>
      <div>
        <input
          step="any"
          className="form-control"
          min={tier.price}
          {...field}
          {...props}
        />
      </div>
      {meta.touched && meta.error ? (
        <div style={{ paddingTop: "7px", color: "red" }}>{meta.error}</div>
      ) : null}
    </div>
  );
}

type SupporterCommercialProps = {
  tier: TierInfo;
  user?: UserInfo;
  mtcaptcha_site_key: string;
  csrf_token: string;
  initial_form_data: any;
  initial_errors: any;
  existing_user: boolean;
};

function SignupCommercial({
  tier,
  user,
  csrf_token,
  mtcaptcha_site_key,
  initial_form_data,
  initial_errors,
  existing_user,
}: SupporterCommercialProps): JSX.Element {
  const accountTypeUrl = "/supporters/account-type";
  const nonCommercialUrl = "/signup/noncommercial";

  const baseInitialValues = {
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
    address_street: Yup.string().required("You need to specify street."),
    address_city: Yup.string().required("You need to specify city."),
    address_state: Yup.string().required("You need to specify state/province."),
    address_postcode: Yup.string().required("You need to specify postcode."),
    address_country: Yup.string().required("You need to specify country."),
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
    mtcaptcha: mtcaptcha_site_key ? Yup.string().required() : Yup.string(),
  };

  const validationSchema = Yup.object(
    existing_user
      ? baseValidationSchema
      : {
          ...baseValidationSchema,
          username: Yup.string().required("Username is required!"),
          email: Yup.string().email().required("Email address is required!"),
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
        }
  );

  return (
    <AuthCardContainer>
      <div className="auth-card-container">
        <div className="auth-card">
          <h1 className="page-title text-center">
            {existing_user ? "Become a Supporter" : "Sign up"}{" "}
            <small>Commercial</small>
          </h1>
          <div className="h4 text-center">access all MetaBrainz projects</div>
          <p>
            <strong>Note:</strong> Signing up for any tier other than the{" "}
            <i>Stealth startup</i> tier will publicly list your company on this
            web site. However, we will not publish any of your private details.
          </p>

          <Formik
            initialValues={initialValues}
            initialErrors={initial_errors}
            initialTouched={initial_errors}
            validationSchema={validationSchema}
            onSubmit={() => {}}
          >
            {({ errors, isValid, dirty }) => (
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

                <div className="form-horizontal">
                  <div className="form-group">
                    <div className="col-xs-6 col-sm-4 control-label">
                      <strong>Account type</strong>
                    </div>
                    <div className="col-xs-6 col-sm-5">
                      <div
                        className="label label-success"
                        style={{ padding: "10px" }}
                      >
                        Commercial
                      </div>
                    </div>
                  </div>
                  <div className="form-group">
                    <div className="col-xs-6 col-sm-4 control-label">
                      <strong>Selected tier</strong>
                    </div>
                    <div
                      className="col-xs-6 col-sm-5"
                      style={{ paddingTop: "7px" }}
                    >
                      <b>{tier.name}</b>
                      <p className="text-muted">${tier.price}/month and up</p>
                    </div>
                    <div
                      className="btn btn-link col-xs-offset-1 col-sm-offset-4"
                      style={{ marginTop: "10px" }}
                    >
                      <a href={accountTypeUrl}>Change account type or tier</a>
                    </div>
                  </div>
                </div>

                <hr />

                {existing_user && user ? (
                  <div className="form-group">
                    <div className="alert alert-info">
                      <strong>Your account:</strong> {user.username} (
                      {user.email})
                    </div>
                  </div>
                ) : (
                  <>
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
                      required
                    />

                    <AuthCardPasswordInput
                      label="Password"
                      name="password"
                      id="password"
                      required
                      labelLink={
                        <div className="small text-muted form-label-link">
                          Must be at least 8 characters
                        </div>
                      }
                    />

                    <AuthCardPasswordInput
                      label="Confirm Password"
                      name="confirm_password"
                      id="confirm_password"
                      required
                    />
                  </>
                )}

                {existing_user && (
                  <AuthCardTextInput
                    type="text"
                    id="contact_name"
                    name="contact_name"
                    label="Contact Name"
                    required
                  />
                )}

                <AuthCardTextInput
                  type="text"
                  id="org_name"
                  name="org_name"
                  label="Organization name"
                  required
                >
                  <p className="text-muted">
                    If you don&apos;t have an organization name, you probably
                    want to {existing_user ? "become a supporter" : "sign up"}{" "}
                    as a{" "}
                    <a href={nonCommercialUrl}>non-commercial / personal</a>{" "}
                    {existing_user ? "supporter" : "user"}.
                  </p>
                </AuthCardTextInput>

                <TextAreaInput
                  id="org_desc"
                  name="org_desc"
                  label="Organization description"
                  required
                >
                  <p className="text-muted">
                    Please tell us a little about your company and whether you
                    plan to use our{" "}
                    <a href="https://musicbrainz.org/doc/Development/XML_Web_Service/Version_2">
                      API
                    </a>{" "}
                    or to{" "}
                    <a href="https://musicbrainz.org/doc/MusicBrainz_Server/Setup">
                      host your own copy
                    </a>{" "}
                    of the data.
                  </p>
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
                  <p className="text-muted">
                    Image should be about 250 pixels wide on a white or
                    transparent background. We will host it on our site.
                  </p>
                </AuthCardTextInput>

                <AuthCardTextInput
                  type="text"
                  id="api_url"
                  name="api_url"
                  label="API URL"
                >
                  <p className="text-muted">
                    URL to where developers can use your APIs using MusicBrainz
                    IDs, if available..
                  </p>
                </AuthCardTextInput>

                <TextAreaInput
                  id="usage_desc"
                  name="usage_desc"
                  label="Your project"
                  maxLength={150}
                  rows={6}
                  required
                  placeholder="(max 150 characters)"
                >
                  <p className="text-muted">
                    Can you please tell us more about the project in which
                    you&apos;d like to use our data? Do you plan to self host
                    the data or use our APIs?
                  </p>
                </TextAreaInput>

                <AmountPledgedField
                  id="amount_pledged"
                  name="amount_pledged"
                  type="number"
                  tier={tier}
                />
                <hr />

                <h4>Billing address</h4>

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

                <div className="text-center small">
                  <p>
                    The following information will be shown publicly:
                    organization name, logo, website and API URLs, data usage
                    description.
                  </p>
                  <p>
                    We&apos;ll send you more details about payment process once
                    your application is approved.
                  </p>
                </div>

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
                    disabled={!isValid || !dirty}
                  >
                    {existing_user ? "Become a Supporter" : "Sign up"}
                  </button>
                </div>
              </form>
            )}
          </Formik>
          <div className="auth-card-footer">
            {existing_user ? (
              <div className="small">
                <a href="/profile">Back to profile</a>
              </div>
            ) : (
              <>
                <div className="small">
                  Not a supporter? <a href="/signup">Create a user account </a>
                </div>
                <div className="small">
                  Already have an account? <a href="/login">Sign in </a>
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
    tier,
    user,
    mtcaptcha_site_key,
    csrf_token,
    initial_form_data,
    initial_errors,
    existing_user,
  } = reactProps;

  const renderRoot = createRoot(domContainer!);
  renderRoot.render(
    <SignupCommercial
      tier={tier}
      user={user}
      mtcaptcha_site_key={mtcaptcha_site_key}
      csrf_token={csrf_token}
      initial_form_data={initial_form_data}
      initial_errors={initial_errors}
      existing_user={existing_user}
    />
  );
});
