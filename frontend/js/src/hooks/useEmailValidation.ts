import { useState, useCallback, useRef, useMemo, useEffect } from "react";
import debounce from "lodash/debounce";
import { useTranslation } from "react-i18next";
import { checkEmail } from "../api/emailValidation";

const DEBOUNCE_DELAY_MS = 500;

/**
 * Custom hook for async email validation
 * Returns validation state and a validate function for use with Formik
 */
function useEmailValidation() {
  const { t } = useTranslation();
  const [isValidatingEmail, setIsValidatingEmail] = useState(false);
  const [lastValidatedEmail, setLastValidatedEmail] = useState<string | null>(
    null
  );
  const [emailValidationCache, setEmailValidationCache] = useState<
    Record<string, string | null>
  >({});

  const pendingResolveRef = useRef<
    ((value: string | undefined) => void) | null
  >(null);

  const debouncedApiCall = useMemo(
    () =>
      debounce(
        async (
          email: string,
          resolve: (error: string | undefined) => void,
          cacheResult: (emailKey: string, error: string | null) => void
        ) => {
          pendingResolveRef.current = null;
          try {
            const result = await checkEmail(email);
            let reasonMessage: string | null = null;
            if (result.reason === "email_taken") {
              reasonMessage = t("This email address is already registered.");
            } else if (result.reason === "domain_blacklisted") {
              reasonMessage = t(
                "Registration from this email domain is not allowed."
              );
            }
            const errorMessage = result.valid
              ? null
              : reasonMessage || result.error || t("Email validation failed");

            cacheResult(email, errorMessage);
            resolve(errorMessage || undefined);
          } finally {
            setIsValidatingEmail(false);
          }
        },
        DEBOUNCE_DELAY_MS
      ),
    [t]
  );

  // Clean up debounced function on unmount
  useEffect(() => {
    return () => {
      debouncedApiCall.cancel();
    };
  }, [debouncedApiCall]);

  const validateEmailAsync = useCallback(
    async (email: string): Promise<string | undefined> => {
      debouncedApiCall.cancel();

      // If there's a pending promise, resolve it with undefined to avoid blocking
      if (pendingResolveRef.current) {
        pendingResolveRef.current(undefined);
        pendingResolveRef.current = null;
      }

      if (!email) {
        return t("Email address is required!");
      }
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(email)) {
        return t("Invalid email address");
      }

      if (emailValidationCache[email] !== undefined) {
        return emailValidationCache[email] || undefined;
      }

      if (lastValidatedEmail === email) {
        return undefined;
      }

      setIsValidatingEmail(true);

      return new Promise((resolve) => {
        pendingResolveRef.current = resolve;

        const cacheResult = (emailKey: string, error: string | null) => {
          setEmailValidationCache((prev) => ({
            ...prev,
            [emailKey]: error,
          }));
          setLastValidatedEmail(emailKey);
        };

        debouncedApiCall(email, resolve, cacheResult);
      });
    },
    [emailValidationCache, lastValidatedEmail, debouncedApiCall, t]
  );

  return {
    isValidatingEmail,
    validateEmailAsync,
  };
}

export default useEmailValidation;
