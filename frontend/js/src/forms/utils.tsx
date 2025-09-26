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

export type OAuthTextInputProps = JSX.IntrinsicElements["input"] &
  FieldConfig & {
    label: string;
  };

export function OAuthTextInput({
  label,
  children,
  ...props
}: OAuthTextInputProps) {
  const [field, meta] = useField(props);
  return (
    <div className="form-group">
      <label className="col-sm-3 control-label">
        {label} {props.required && <span style={{ color: "red" }}>*</span>}
      </label>
      <div className="col-sm-5">
        <input className="form-control" {...field} {...props} />
        {meta.touched && meta.error ? (
          <div style={{ paddingTop: "7px", color: "red" }}>{meta.error}</div>
        ) : null}
      </div>
    </div>
  );
}

export function OAuthScopeDesc(scopes: Array<Scope>) {
  return (
    <ul>
      {/* eslint-disable-next-line react/destructuring-assignment */}
      {scopes.map((scope) => (
        <li>
          {scope.name}: {scope.description}
        </li>
      ))}
    </ul>
  );
}

export type AuthCardContainerProps = {
  children?: any;
};

export function AuthCardContainer({ children }: AuthCardContainerProps) {
  return (
    <section id="auth-page">
      <div className="auth-page-container">
        <div className="icon-pills">
          <div className="icon-pill">
            <img
              src="/static/img/projects/musicbrainz.svg"
              alt="MusicBrainz"
              title="MusicBrainz"
            />
          </div>
          <div className="icon-pill">
            <img
              src="/static/img/projects/listenbrainz.svg"
              alt="ListenBrainz"
              title="ListenBrainz"
            />
          </div>
          <div className="icon-pill">
            <img
              src="/static/img/projects/bookbrainz.svg"
              alt="BookBrainz"
              title="BookBrainz"
            />
          </div>
          <div className="icon-pill">
            <img
              src="/static/img/projects/critiquebrainz.svg"
              alt="CritiqueBrainz"
              title="CritiqueBrainz"
            />
          </div>
          <div className="icon-pill">
            <img
              src="/static/img/projects/picard.svg"
              alt="Picard"
              title="Picard"
            />
          </div>
        </div>
        {children}
      </div>
    </section>
  );
}

export type AuthCardTextInputProps = JSX.IntrinsicElements["input"] &
  FieldConfig & {
    label: string | JSX.Element;
    optionalInputButton?: JSX.Element;
  };

export function AuthCardTextInput({
  label,
  children,
  ...props
}: AuthCardTextInputProps) {
  const [field, meta] = useField(props);
  const { optionalInputButton } = props;
  return (
    <div className="form-group">
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          width: "100%",
        }}
      >
        <label className="form-label" htmlFor={props.id}>
          {label} {props.required && <span style={{ color: "red" }}>*</span>}
        </label>
        {children}
      </div>
      <div className={optionalInputButton ? "input-group" : ""}>
        <input
          className="form-control"
          {...field}
          {...props}
          required={props.required}
        />
        {optionalInputButton}
      </div>
      {meta.touched && meta.error ? (
        <div className="small" style={{ paddingTop: "7px", color: "red" }}>
          {meta.error}
        </div>
      ) : null}
    </div>
  );
}

export function AuthCardPasswordInput({ ...props }: AuthCardTextInputProps) {
  const [passwordVisible, setPasswordVisible] = React.useState(false);
  const glyphIcon = passwordVisible
    ? "glyphicon-eye-close"
    : "glyphicon-eye-open";
  const passwordShowButton = (
    <span className="input-group-btn">
      <button
        className="btn btn-info"
        type="button"
        onClick={() => {
          setPasswordVisible((prev) => !prev);
        }}
      >
        <span className={`glyphicon ${glyphIcon}`} aria-hidden="true" />
      </button>
    </span>
  );
  return (
    <AuthCardTextInput
      {...props}
      type={passwordVisible ? "text" : "password"}
      optionalInputButton={passwordShowButton}
    />
  );
}

export type AuthCardCheckboxInputProps = JSX.IntrinsicElements["input"] &
  FieldConfig & {
    label: string;
  };

export function AuthCardCheckboxInput({
  label,
  children,
  ...props
}: AuthCardCheckboxInputProps) {
  const [field, meta] = useField(props);
  return (
    <div className="form-group">
      <label htmlFor={props.id}>
        <input {...props} {...field} />
        Remember me
      </label>
      {meta.touched && meta.error ? (
        <div style={{ paddingTop: "7px", color: "red" }}>{meta.error}</div>
      ) : null}
    </div>
  );
}
