import { isAuthFailureError } from "../src/services/authError";

describe("isAuthFailureError", () => {
    it("인증 만료/인가 실패 에러를 true로 판별한다", () => {
        expect(isAuthFailureError(new Error("Unauthorized"))).toBe(true);
        expect(isAuthFailureError(new Error("Session expired"))).toBe(true);
    });

    it("기타 에러/비에러 값은 false로 판별한다", () => {
        expect(isAuthFailureError(new Error("Request failed"))).toBe(false);
        expect(isAuthFailureError("Unauthorized")).toBe(false);
        expect(isAuthFailureError(null)).toBe(false);
    });
});
