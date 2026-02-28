// src/services/errorHandler.ts
// API 에러 코드 기반 공통 에러 핸들러

export interface ApiError {
    error_code: string;
    message: string;
}

// Backend ErrorCode 상수와 동기화
export const ErrorCode = {
    TOKEN_EXPIRED: "TOKEN_EXPIRED",
    TOKEN_INVALID: "TOKEN_INVALID",
    REFRESH_TOKEN_EXPIRED: "REFRESH_TOKEN_EXPIRED",
    REFRESH_TOKEN_INVALID: "REFRESH_TOKEN_INVALID",
    GOOGLE_AUTH_FAILED: "GOOGLE_AUTH_FAILED",
    USER_NOT_FOUND: "USER_NOT_FOUND",
    VALIDATION_ERROR: "VALIDATION_ERROR",
    INTERNAL_ERROR: "INTERNAL_ERROR",
} as const;

export type ErrorCodeType = (typeof ErrorCode)[keyof typeof ErrorCode];

/**
 * API 응답에서 에러 정보를 파싱한다.
 */
export const parseApiError = async (res: Response): Promise<ApiError> => {
    try {
        const data = await res.json();
        if (data.error_code) return data as ApiError;
        // FastAPI 기본 HTTPException 형태도 처리
        if (data.detail) return { error_code: "UNKNOWN", message: String(data.detail) };
        return { error_code: "UNKNOWN", message: res.statusText };
    } catch {
        return { error_code: "UNKNOWN", message: res.statusText || "Unknown error" };
    }
};

/**
 * 인증 관련 localStorage를 정리한다.
 */
export const clearAuth = () => {
    if (typeof window === "undefined") return;
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("profile_picture");
    localStorage.removeItem("user_name");
    localStorage.removeItem("user_email");
};

/**
 * 에러 코드에 따라 공통 처리를 수행한다.
 * 반환값: 'retry' (토큰 refresh 후 재시도), 'redirect' (로그인 리다이렉트), 'throw' (호출자에서 처리)
 */
export const handleApiError = (error: ApiError): "retry" | "redirect" | "throw" => {
    switch (error.error_code) {
        case ErrorCode.TOKEN_EXPIRED:
        case ErrorCode.TOKEN_INVALID:
            // refresh 시도 가능
            return "retry";

        case ErrorCode.REFRESH_TOKEN_EXPIRED:
        case ErrorCode.REFRESH_TOKEN_INVALID:
        case ErrorCode.USER_NOT_FOUND:
            // 세션 완전 만료 → 로그인 페이지로 이동
            clearAuth();
            if (typeof window !== "undefined") {
                window.location.href = "/login";
            }
            return "redirect";

        default:
            console.error(`[API Error] ${error.error_code}: ${error.message}`);
            return "throw";
    }
};
