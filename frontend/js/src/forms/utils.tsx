import React, { JSX } from "react";
import { Field, FieldConfig, useField } from "formik";

export type TextInputProps = JSX.IntrinsicElements["input"] &
  FieldConfig & {
    label: string;
  };

export function TextInput({ label, children, ...props }: TextInputProps) {
  const [field, meta] = useField(props);
  return (
    <div className="form-group">
      <label className="col-sm-4 control-label" htmlFor={props.id}>
        {label} {props.required && <span style={{ color: "red" }}>*</span>}
      </label>
      <div className="col-sm-5">
        <input className="form-control" {...field} {...props} />
      </div>
      {children}
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

export type TextAreaInputProps = JSX.IntrinsicElements["textarea"] &
  FieldConfig & {
    label: string;
  };

export function TextAreaInput({
  label,
  children,
  ...props
}: TextAreaInputProps) {
  const [field, meta] = useField(props);
  return (
    <div className="form-group">
      <label className="col-sm-4 control-label" htmlFor={props.id}>
        {label} {props.required && <span style={{ color: "red" }}>*</span>}
      </label>
      <div className="col-sm-5">
        <textarea className="form-control" {...field} {...props} />
      </div>
      {children}
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

export type CheckboxInputProps = JSX.IntrinsicElements["input"] &
  FieldConfig & {
    label: string;
  };

export function CheckboxInput({
  label,
  children,
  ...props
}: CheckboxInputProps) {
  const [field, meta] = useField(props);
  return (
    <div className="form-group">
      <div className="col-sm-offset-4 col-sm-8">
        <div className="checkbox">
          <label htmlFor={props.id}>
            <input {...props} {...field} />
            {children}
          </label>
          {meta.touched && meta.error ? (
            <div style={{ paddingTop: "7px", color: "red" }}>{meta.error}</div>
          ) : null}
        </div>
      </div>
    </div>
  );
}

export type Dataset = {
  id: number;
  name: string;
  description: string;
};

export type DatasetsProps = {
  datasets: Dataset[];
};

export function DatasetsInput({ datasets }: DatasetsProps) {
  return (
    <div className="form-group">
      <div className="col-sm-4 control-label">
        <strong>Datasets</strong>
      </div>
      <div className="col-sm-5">
        <div className="list-group">
          {datasets.map((dataset) => (
            <div
              className="form-check list-group-item"
              key={`datasets-${dataset.id}`}
            >
              <h4 className="list-group-item-heading">
                <Field
                  className="form-check-input"
                  id={`datasets-${dataset.id}`}
                  name="datasets"
                  type="checkbox"
                  value={`${dataset.id}`}
                />
                <label
                  className="form-check-label"
                  htmlFor={`datasets-${dataset.id}`}
                >
                  {" "}
                  {dataset.name}
                </label>
              </h4>
              <p className="list-group-item-text">{dataset.description}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
