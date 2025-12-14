import React, { useEffect, useRef, JSX } from "react";
import { useField, useFormikContext } from "formik";

declare global {
  interface Window {
    mtcaptchaConfig?: {
      sitekey: string;
      renderQueue?: string[];
      "verified-callback"?: string;
      "verifyexpired-callback"?: string;
      "error-callback"?: string;
    };
    mtcaptcha?: any;
  }
}

type MTCaptchaProps = {
  sitekey: string;
  size?: "compact" | "normal";
  fieldName: string;
};

function MTCaptcha({
  sitekey,
  size = "normal",
  fieldName,
}: MTCaptchaProps): JSX.Element | null {
  const [field] = useField(fieldName);
  const { setFieldValue } = useFormikContext();
  const containerRef = useRef<HTMLDivElement>(null);
  const callbackIdRef = useRef<string>(
    `mtcaptcha_${Math.random().toString(36).substring(7)}`
  );

  useEffect(() => {
    // Don't set up captcha if sitekey is not configured
    if (!sitekey) {
      return () => {};
    }

    const callbackId = callbackIdRef.current;

    (window as any)[`${callbackId}_verified`] = (token: string) => {
      const { verifiedToken } = token as any;
      setFieldValue(fieldName, verifiedToken);
    };

    (window as any)[`${callbackId}_expired`] = () => {
      setFieldValue(fieldName, null);
    };

    (window as any)[`${callbackId}_error`] = () => {
      setFieldValue(fieldName, null);
    };

    if (!document.querySelector('script[src*="mtcaptcha.min.js"]')) {
      const script1 = document.createElement("script");
      script1.src =
        "https://service.mtcaptcha.com/mtcv1/client/mtcaptcha.min.js";
      script1.async = true;
      const targetElement =
        document.getElementsByTagName("head")[0] ||
        document.getElementsByTagName("body")[0];
      targetElement.appendChild(script1);

      const script2 = document.createElement("script");
      script2.src =
        "https://service2.mtcaptcha.com/mtcv1/client/mtcaptcha2.min.js";
      script2.async = true;
      targetElement.appendChild(script2);

      script2.onload = () => {
        if (containerRef.current) {
          containerRef.current.classList.add("mtcaptcha");
        }
      };
    } else if (containerRef.current) {
      containerRef.current.classList.add("mtcaptcha");
    }

    return () => {
      delete (window as any)[`${callbackId}_verified`];
      delete (window as any)[`${callbackId}_expired`];
      delete (window as any)[`${callbackId}_error`];
    };
  }, [sitekey, fieldName, setFieldValue]);

  // Don't render captcha if sitekey is not configured
  if (!sitekey) {
    return null;
  }

  return (
    <>
      <input type="hidden" {...field} />
      <div
        ref={containerRef}
        className={size === "compact" ? "mtcaptcha-compact" : ""}
        data-sitekey={sitekey}
        data-verified-callback={`${callbackIdRef.current}_verified`}
        data-verifyexpired-callback={`${callbackIdRef.current}_expired`}
        data-error-callback={`${callbackIdRef.current}_error`}
      />
    </>
  );
}

export default MTCaptcha;
