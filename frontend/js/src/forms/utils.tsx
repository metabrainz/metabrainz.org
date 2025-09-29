import React, { JSX } from "react";
import { Field, FieldConfig, useField } from "formik";

export type TextInputProps = JSX.IntrinsicElements["input"] &
  FieldConfig & {
    label: string;
  };

export function TextInput({ label, children, ...props }: TextInputProps) {
  const [field, meta] = useField(props);
  const hasError = meta.touched && meta.error;
  return (
    <div className={`form-group ${hasError ? "has-error" : ""}`}>
      <label className="col-sm-4 control-label" htmlFor={props.id}>
        {label} {props.required && <span style={{ color: "red" }}>*</span>}
      </label>
      <div className="col-sm-5">
        <input className="form-control" {...field} {...props} />
      </div>
      {children}
      {hasError ? (
        <div className="col-sm-offset-4 col-sm-5 small help-block text-danger">
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
  const hasError = meta.touched && meta.error;
  return (
    <div className={`form-group ${hasError ? "has-error" : ""}`}>
      <label className="control-label" htmlFor={props.id}>
        {label} {props.required && <span style={{ color: "red" }}>*</span>}
      </label>
      {children}
      <textarea className="form-control" {...field} {...props} />
      {hasError ? (
        <div className="small help-block text-danger">{meta.error}</div>
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
  const hasError = meta.touched && meta.error;
  return (
    <div className={`form-group ${hasError ? "has-error" : ""}`}>
      <div>
        <div className="checkbox">
          <label htmlFor={props.id}>
            <input {...props} {...field} />
            {children}
          </label>
          {hasError ? (
            <div className="small help-block text-danger">{meta.error}</div>
          ) : null}
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
  const hasError = meta.touched && meta.error;
  return (
    <div className={`form-group ${hasError ? "has-error" : ""}`}>
      <label className="col-sm-3 control-label">
        {label} {props.required && <span style={{ color: "red" }}>*</span>}
      </label>
      <div className="col-sm-9">
        <input className="form-control" {...field} {...props} />
        {hasError ? (
          <div className="small help-block text-danger">{meta.error}</div>
        ) : null}
      </div>
    </div>
  );
}

export type AuthCardTextInputProps = JSX.IntrinsicElements["input"] &
  FieldConfig & {
    label: string | JSX.Element;
    labelLink?: string | JSX.Element;
    optionalInputButton?: JSX.Element;
  };

export function AuthCardTextInput({
  label,
  labelLink,
  children,
  ...props
}: AuthCardTextInputProps) {
  const [field, meta] = useField(props);
  const hasError = meta.touched && meta.error;
  const { optionalInputButton, ...otherProps } = props;
  const labelElement = (
    <label className="control-label" htmlFor={props.id}>
      {label} {props.required && <span style={{ color: "red" }}>*</span>}
    </label>
  );
  return (
    <div className={`form-group ${hasError ? "has-error" : ""}`}>
      {labelLink ? (
        <div className="label-with-link">
          {labelElement}
          {labelLink}
        </div>
      ) : (
        labelElement
      )}
      {children}
      <div className={optionalInputButton ? "input-group" : ""}>
        <input
          className="form-control"
          {...field}
          {...otherProps}
          required={props.required}
        />
        {optionalInputButton}
      </div>
      {hasError ? (
        <div className="small help-block text-danger">{meta.error}</div>
      ) : null}
    </div>
  );
}

export function AuthCardPasswordInput({ ...props }: AuthCardTextInputProps) {
  const [passwordVisible, setPasswordVisible] = React.useState(false);
  const glyphIcon = passwordVisible
    ? "glyphicon-eye-close"
    : "glyphicon-eye-open";
  const title = passwordVisible ? "Hide password" : "Show password";
  const passwordShowButton = (
    <span className="input-group-btn">
      <button
        className="btn btn-info"
        title={title}
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
  const hasError = meta.touched && meta.error;
  return (
    <div className={`form-group ${hasError ? "has-error" : ""}`}>
      <label className="control-label" htmlFor={props.id}>
        <input {...props} {...field} />
        Remember me
      </label>
      {hasError ? (
        <div className="small help-block text-danger">{meta.error}</div>
      ) : null}
    </div>
  );
}
export type DatasetsProps = {
  datasets: Dataset[];
};

export function DatasetsInput({ datasets }: DatasetsProps) {
  return (
    <div className="list-group small" id="datasets">
      {datasets.map((dataset) => (
        <div
          className="form-check list-group-item"
          key={`datasets-${dataset.id}`}
        >
          <h5 className="checkbox-inline list-group-item-heading">
            <label
              className="form-check-label"
              htmlFor={`datasets-${dataset.id}`}
            >
              <Field
                className="form-check-input"
                id={`datasets-${dataset.id}`}
                name="datasets"
                type="checkbox"
                value={`${dataset.id}`}
              />{" "}
              {dataset.name}
            </label>
          </h5>
          <p className="list-group-item-text">{dataset.description}</p>
        </div>
      ))}
    </div>
  );
}

export function OAuthScopeDesc(scopes: Array<Scope>) {
  return (
    <ul>
      {/* eslint-disable-next-line react/destructuring-assignment */}
      {scopes.map((scope) => (
        <li key={scope.name}>
          {scope.name}: {scope.description}
        </li>
      ))}
    </ul>
  );
}

export type AuthCardContainerProps = {
  children?: any;
};

export function ProjectIconPills() {
  return (
    <div className="icon-pills">
      <div className="icon-pill" data-logo-width="160">
        <img
          src="/static/img/logos/musicbrainz.svg"
          alt="MusicBrainz"
          title="MusicBrainz"
        />
      </div>
      <div className="icon-pill" data-logo-width="162">
        <img
          src="/static/img/logos/listenbrainz.svg"
          alt="ListenBrainz"
          title="ListenBrainz"
        />
      </div>
      <div className="icon-pill" data-logo-width="151">
        <img
          src="/static/img/logos/bookbrainz.svg"
          alt="BookBrainz"
          title="BookBrainz"
        />
      </div>
      <div className="icon-pill" data-logo-width="177">
        <img
          src="/static/img/logos/critiquebrainz.svg"
          alt="CritiqueBrainz"
          title="CritiqueBrainz"
        />
      </div>
      <div className="icon-pill" data-logo-width="101">
        <img src="/static/img/logos/picard.svg" alt="Picard" title="Picard" />
      </div>
    </div>
  );
}

export function AuthCardContainer({ children }: AuthCardContainerProps) {
  return (
    <section id="auth-page">
      <div className="auth-page-container">
        <ProjectIconPills />
        {children}
      </div>
    </section>
  );
}
