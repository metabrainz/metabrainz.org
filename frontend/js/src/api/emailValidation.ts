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
        error: errorData.error,
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
