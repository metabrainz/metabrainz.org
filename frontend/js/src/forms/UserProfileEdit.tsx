import { Formik } from "formik";
import React, { JSX } from "react";
import { createRoot } from "react-dom/client";
import * as Yup from "yup";
import { getPageProps } from "../utils";
import { Dataset, DatasetsInput, TextInput } from "./utils";

type UserProfileEditProps = {
  csrf_token: string;
  initial_form_data: any;
  initial_errors: any;
};

function UserProfileEdit({
  csrf_token,
  initial_form_data,
  initial_errors,
}: UserProfileEditProps): JSX.Element {
  return (
    <>
      <h1 className="page-title">Your Profile</h1>
      <h2>Edit contact information</h2>

      <Formik
        initialValues={{
          email: initial_form_data.email ?? "",
          csrf_token,
        }}
        initialErrors={initial_errors}
        initialTouched={initial_errors}
        validationSchema={Yup.object({
          contact_email: Yup.string()
            .email()
            .required("Email address is required!"),
        })}
        onSubmit={() => {}}
      >
        {({ errors }) => (
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

            <TextInput
              type="email"
              id="email"
              name="email"
              label="E-mail address"
              required
            />

            <div className="form-group">
              <div className="col-sm-offset-4 col-sm-10">
                <button type="submit" className="btn btn-primary">
                  Update
                </button>
              </div>
            </div>
          </form>
        )}
      </Formik>
    </>
  );
}

document.addEventListener("DOMContentLoaded", () => {
  const { domContainer, reactProps, globalProps } = getPageProps();
  const { csrf_token, initial_form_data, initial_errors } = reactProps;

  const renderRoot = createRoot(domContainer!);
  renderRoot.render(
    <UserProfileEdit
      csrf_token={csrf_token}
      initial_form_data={initial_form_data}
      initial_errors={initial_errors}
    />
  );
});
