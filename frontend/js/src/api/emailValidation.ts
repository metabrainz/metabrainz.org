export type EmailValidationResponse = {
  valid: boolean;
  reason: "email_taken" | "domain_blacklisted" | null;
  error?: string;
};

/**
 * Check if an email is valid for registration.
 * Validates against:
 * - Already registered emails
 * - Blacklisted email domains
 *
 * @param email - The email address to validate
 * @returns Promise with validation result
 */
export async function checkEmail(
  email: string
): Promise<EmailValidationResponse> {
  try {
    const response = await fetch("/check-email", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ email }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      return {
        valid: false,
        reason: null,
        error: errorData.error || "Failed to validate email",
      };
    }

    return await response.json();
  } catch (error) {
    // Network error or other issue - don't block form submission
    // Let server-side validation handle it
    console.error("Email validation API error:", error);
    return {
      valid: true,
      reason: null,
    };
  }
}

/**
 * Get a user-friendly error message based on the validation reason
 */
export function getEmailValidationErrorMessage(
  reason: "email_taken" | "domain_blacklisted" | null
): string | null {
  switch (reason) {
    case "email_taken":
      return "This email address is already registered.";
    case "domain_blacklisted":
      return "Registration from this email domain is not allowed.";
    default:
      return null;
  }
}
