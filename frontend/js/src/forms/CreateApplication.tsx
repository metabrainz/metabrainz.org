import { Field, getIn, FieldArray, Formik } from "formik";
import React, { JSX } from "react";
import { useTranslation } from "react-i18next";
import * as Yup from "yup";
import { getPageProps, renderRoot } from "../utils";
import { OAuthTextInput } from "./utils";

type CreateApplicationProps = {
  csrf_token: string;
  is_edit_mode: boolean;
  initial_form_data: any;
  initial_errors: any;
};

function NestedErrorMessage({ name }: { name: string }) {
  return (
    <Field name={name}>
      {({ form }: { form: any }) => {
        const error = getIn(form.errors, name);
        const touch = getIn(form.touched, name);
        return touch && error ? (
          <div style={{ paddingTop: "7px", color: "red" }}>{error}</div>
        ) : null;
      }}
    </Field>
  );
}

function CreateApplication({
  csrf_token,
  is_edit_mode,
  initial_form_data,
  initial_errors,
}: CreateApplicationProps): JSX.Element {
  const { t } = useTranslation();

  return (
    <>
      <h2>
        {is_edit_mode
          ? `${t("Edit application")} ${initial_form_data.client_name}`
          : t("Create new application")}
      </h2>
      <hr />
      <Formik
        initialValues={{
          client_name: initial_form_data.client_name ?? "",
          description: initial_form_data.description ?? "",
          website: initial_form_data.website ?? "",
          redirect_uris: initial_form_data.redirect_uris ?? [],
          csrf_token,
        }}
        initialErrors={initial_errors}
        initialTouched={initial_errors}
        validationSchema={Yup.object({
          client_name: Yup.string()
            .required(t("Application name is required."))
            .min(
              3,
              t("Application name needs to be at least 3 characters long.")
            )
            .max(
              64,
              t("Application name needs to be at most 64 characters long.")
            ),
          description: Yup.string()
            .required(t("Application description is required."))
            .min(
              3,
              t(
                "Application description needs to be at least 3 characters long."
              )
            )
            .max(
              512,
              t("Application description needs to be at most 512 characters long.")
            ),
          website: Yup.string().required(t("Homepage is required.")),
          redirect_uris: Yup.array()
            .of(
              Yup.string().required(
                t("Authorization callback URL cannot be empty.")
              )
            )
            .min(1, t("Authorization callback URL is required.")),
        })}
        onSubmit={() => {}}
      >
        {({ errors, values }) => (
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

            <OAuthTextInput
              label={t("Application Name")}
              id="client_name"
              name="client_name"
              type="text"
              required
            />

            <OAuthTextInput
              label={t("Description")}
              id="description"
              name="description"
              type="text"
              required
            />

            <OAuthTextInput
              label={t("Homepage")}
              id="website"
              name="website"
              type="text"
              required
            />

            <div className="form-group">
              <label className="col-sm-3 control-label" htmlFor="redirect_uris">
                {t("Redirect URIs")} <span style={{ color: "red" }}>*</span>
              </label>
              <div className="col-sm-9">
                <FieldArray name="redirect_uris">
                  {({ insert, remove, push }) => {
                    return values.redirect_uris &&
                      values.redirect_uris.length > 0 ? (
                      values.redirect_uris.map(
                        (redirect_uri: string, index: number) => {
                          return (
                            <div key={`${index}`}>
                              <Field
                                className="form-control"
                                name={`redirect_uris.${index}`}
                              />
                              <NestedErrorMessage
                                name={`redirect_uris.${index}`}
                              />
                              <button
                                type="button"
                                className="btn btn-default"
                                style={{ margin: "4px" }}
                                onClick={() => remove(index)}
                              >
                                -
                              </button>
                              <button
                                type="button"
                                className="btn btn-default"
                                style={{ margin: "4px" }}
                                onClick={() => insert(index + 1, "")}
                              >
                                +
                              </button>
                            </div>
                          );
                        }
                      )
                    ) : (
                      <button
                        type="button"
                        className="btn btn-default"
                        onClick={() => push("")}
                      >
                        {t("Add a redirect URI")}
                      </button>
                    );
                  }}
                </FieldArray>
                {typeof errors.redirect_uris === "string" ? (
                  <NestedErrorMessage name="redirect_uris" />
                ) : null}
              </div>
            </div>

            <div className="form-group">
              <div className="col-sm-offset-3 col-sm-10">
                <button type="submit" className="btn btn-primary">
                  {is_edit_mode
                    ? t("Save changes")
                    : t("Create application")}
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
  const { csrf_token, is_edit_mode, initial_form_data, initial_errors } =
    reactProps;

  renderRoot(
    domContainer!,
    <CreateApplication
      csrf_token={csrf_token}
      is_edit_mode={is_edit_mode}
      initial_form_data={initial_form_data}
      initial_errors={initial_errors}
    />
  );
});
