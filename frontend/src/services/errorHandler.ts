// src/services/errorHandler.ts
// API 에러 코드 기반 공통 에러 핸들러

export interface ApiError {
    error_code: number | string;
    message: string;
    status?: number;
}

// Backend ErrorCode 상수와 동기화
export const ErrorCode = {
    TOKEN_EXPIRED: 1001,
    TOKEN_INVALID: 1002,
    REFRESH_TOKEN_EXPIRED: 1003,
    REFRESH_TOKEN_INVALID: 1004,
    GOOGLE_AUTH_FAILED: 1005,
    USER_NOT_FOUND: 2001,
    VALIDATION_ERROR: 3001,
    INTERNAL_ERROR: 5001,
} as const;

export type ErrorCodeType = (typeof ErrorCode)[keyof typeof ErrorCode];

const LEGACY_ERROR_CODE = {
    TOKEN_EXPIRED: "TOKEN_EXPIRED",
    TOKEN_INVALID: "TOKEN_INVALID",
    REFRESH_TOKEN_EXPIRED: "REFRESH_TOKEN_EXPIRED",
    REFRESH_TOKEN_INVALID: "REFRESH_TOKEN_INVALID",
    USER_NOT_FOUND: "USER_NOT_FOUND",
} as const;

const normalizeErrorCode = (code: number | string): number | string => {
    if (typeof code === "number") return code;
    const asNum = Number(code);
    if (!Number.isNaN(asNum)) return asNum;
    return code;
};

/**
 * API 응답에서 에러 정보를 파싱한다.
 */
export const parseApiError = async (res: Response): Promise<ApiError> => {
    try {
        const data = await res.json();
        if (data?.error_code !== undefined) {
            return {
                error_code: data.error_code as number | string,
                message: String(data.message ?? res.statusText ?? "Unknown error"),
                status: res.status,
            };
        }
        // FastAPI 기본 HTTPException 형태도 처리
        if (data?.detail) return { error_code: "UNKNOWN", message: String(data.detail), status: res.status };
        return { error_code: "UNKNOWN", message: res.statusText, status: res.status };
    } catch {
        return { error_code: "UNKNOWN", message: res.statusText || "Unknown error", status: res.status };
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
    const code = normalizeErrorCode(error.error_code);

    switch (code) {
        case ErrorCode.TOKEN_EXPIRED:
        case ErrorCode.TOKEN_INVALID:
        case LEGACY_ERROR_CODE.TOKEN_EXPIRED:
        case LEGACY_ERROR_CODE.TOKEN_INVALID:
            // refresh 시도 가능
            return "retry";

        case ErrorCode.REFRESH_TOKEN_EXPIRED:
        case ErrorCode.REFRESH_TOKEN_INVALID:
        case ErrorCode.USER_NOT_FOUND:
        case LEGACY_ERROR_CODE.REFRESH_TOKEN_EXPIRED:
        case LEGACY_ERROR_CODE.REFRESH_TOKEN_INVALID:
        case LEGACY_ERROR_CODE.USER_NOT_FOUND:
            // 세션 완전 만료 → 로그인 페이지로 이동
            clearAuth();
            if (typeof window !== "undefined") {
                window.location.href = "/signup";
            }
            return "redirect";

        default:
            // 인증 미들웨어에서 내려오는 401(코드 불명확/기타)도 refresh 1회 시도
            if (error.status === 401) return "retry";
            console.error(`[API Error] ${error.error_code}: ${error.message}`);
            return "throw";
    }
};
