import { Formik } from "formik";
import React, { JSX } from "react";
import { createRoot } from "react-dom/client";
import * as Yup from "yup";
import { getPageProps } from "../utils";
import { Dataset, DatasetsInput, TextInput } from "./utils";

type SupporterProfileEditProps = {
  datasets: Dataset[];
  is_commercial: boolean;
  csrf_token: string;
  initial_form_data: any;
  initial_errors: any;
};

function SupporterProfileEdit({
  datasets,
  is_commercial,
  csrf_token,
  initial_form_data,
  initial_errors,
}: SupporterProfileEditProps): JSX.Element {
  return (
    <>
      <h1 className="page-title">Your Profile</h1>
      <h2>Edit contact information</h2>

      <Formik
        initialValues={{
          datasets:
            initial_form_data.datasets?.map((x: number) => x.toString()) ?? [],
          contact_name: initial_form_data.contact_name ?? "",
          contact_email: initial_form_data.contact_email ?? "",
          csrf_token,
        }}
        initialErrors={initial_errors}
        initialTouched={initial_errors}
        validationSchema={Yup.object({
          contact_name: Yup.string().required("Contact name is required!"),
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

            {!is_commercial && <DatasetsInput datasets={datasets} />}

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
  const {
    datasets,
    is_commercial,
    csrf_token,
    initial_form_data,
    initial_errors,
  } = reactProps;

  const renderRoot = createRoot(domContainer!);
  renderRoot.render(
    <SupporterProfileEdit
      datasets={datasets}
      is_commercial={is_commercial}
      csrf_token={csrf_token}
      initial_form_data={initial_form_data}
      initial_errors={initial_errors}
    />
  );
});
