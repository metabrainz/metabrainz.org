import { useState, useCallback, useRef, useMemo, useEffect } from "react";
import debounce from "lodash/debounce";
import {
  checkEmail,
  getEmailValidationErrorMessage,
} from "../api/emailValidation";

const DEBOUNCE_DELAY_MS = 500;

/**
 * Custom hook for async email validation
 * Returns validation state and a validate function for use with Formik
 */
function useEmailValidation() {
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
            const errorMessage = result.valid
              ? null
              : getEmailValidationErrorMessage(result.reason) ||
                result.error ||
                "Email validation failed";

            cacheResult(email, errorMessage);
            resolve(errorMessage || undefined);
          } finally {
            setIsValidatingEmail(false);
          }
        },
        DEBOUNCE_DELAY_MS
      ),
    []
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
        return "Email address is required!";
      }
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(email)) {
        return "Invalid email address";
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
    [emailValidationCache, lastValidatedEmail, debouncedApiCall]
  );

  return {
    isValidatingEmail,
    validateEmailAsync,
  };
}

export default useEmailValidation;
