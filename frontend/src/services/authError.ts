const AUTH_FAILURE_MESSAGES = new Set(["Unauthorized", "Session expired"]);

export const isAuthFailureError = (error: unknown): error is Error => {
    return error instanceof Error && AUTH_FAILURE_MESSAGES.has(error.message);
};
