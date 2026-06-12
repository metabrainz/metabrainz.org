import { Formik } from "formik";
import React, { JSX } from "react";
import { useTranslation } from "react-i18next";
import * as Yup from "yup";
import { getPageProps, renderRoot } from "../utils";
import { DatasetsInput, TextInput } from "./utils";

type ProfileEditProps = {
  datasets: Dataset[];
  is_supporter: boolean;
  is_commercial: boolean;
  csrf_token: string;
  initial_form_data: any;
  initial_errors: any;
};

function ProfileEdit({
  datasets,
  is_commercial,
  is_supporter,
  csrf_token,
  initial_form_data,
  initial_errors,
}: ProfileEditProps): JSX.Element {
  const { t } = useTranslation();
  const schema: any = {
    email: Yup.string().email().required(t("Email address is required!")),
  };
  if (is_supporter) {
    schema.contact_name = Yup.string().required(t("Contact name is required!"));
  }
  return (
    <>
      <h1 className="page-title">{t("Your Profile")}</h1>
      <h2>{t("Edit contact information")}</h2>
      <Formik
        initialValues={{
          datasets:
            initial_form_data.datasets?.map((x: number) => x.toString()) ?? [],
          contact_name: initial_form_data?.contact_name ?? "",
          email: initial_form_data?.email ?? "",
          csrf_token,
        }}
        initialErrors={initial_errors}
        initialTouched={initial_errors}
        validationSchema={Yup.object(schema)}
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

            {is_supporter && (
              <TextInput
                type="text"
                id="contact_name"
                name="contact_name"
                label={t("Contact Name")}
                required
              />
            )}

            <TextInput
              type="email"
              id="email"
              name="email"
              label={is_supporter ? t("Contact Email") : t("Email")}
              required
            />
            <br />

            {is_supporter && !is_commercial && (
              <div className="form-group">
                <div className="col-sm-4 control-label">
                  <strong>{t("Datasets")}</strong>
                </div>
                <div className="col-sm-5">
                  <DatasetsInput datasets={datasets} />
                </div>
              </div>
            )}

            <div className="form-group">
              <div
                className="col-sm-offset-4 col-sm-5"
                style={{ display: "flex", gap: "10px" }}
              >
                <a
                  href="/profile"
                  className="btn btn-default"
                  style={{ flex: 1, textAlign: "center" }}
                >
                  {t("Cancel")}
                </a>
                <button
                  type="submit"
                  className="btn btn-primary"
                  style={{ flex: 1 }}
                >
                  {t("Update")}
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
  const { domContainer, reactProps } = getPageProps();
  const {
    datasets,
    is_commercial,
    is_supporter,
    csrf_token,
    initial_form_data,
    initial_errors,
  } = reactProps;

  renderRoot(
    domContainer!,
    <ProfileEdit
      datasets={datasets}
      is_supporter={is_supporter}
      is_commercial={is_commercial}
      csrf_token={csrf_token}
      initial_form_data={initial_form_data}
      initial_errors={initial_errors}
    />
  );
});
