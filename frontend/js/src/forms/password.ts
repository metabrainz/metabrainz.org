export const BCRYPT_MAX_PASSWORD_BYTES = 72;

export function passwordExceedsBcryptByteLimit(
  value: string | undefined
): boolean {
  return (
    typeof value === "string" &&
    new TextEncoder().encode(value).byteLength > BCRYPT_MAX_PASSWORD_BYTES
  );
}

export function setPasswordByteLimitValidity(
  input: HTMLInputElement,
  errorMessage: string
): void {
  input.setCustomValidity(
    passwordExceedsBcryptByteLimit(input.value) ? errorMessage : ""
  );
}
