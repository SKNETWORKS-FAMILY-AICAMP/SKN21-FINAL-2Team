import { handleApiError } from "../src/services/errorHandler";

describe("handleApiError", () => {
    const originalWindow = global.window;

    beforeEach(() => {
        jest.spyOn(console, "error").mockImplementation(() => undefined);
        jest.spyOn(console, "warn").mockImplementation(() => undefined);
    });

    afterEach(() => {
        jest.restoreAllMocks();
        global.window = originalWindow;
    });

    it("비핵심 API는 warn 레벨로 로그를 낮출 수 있다", () => {
        const result = handleApiError(
            { error_code: "UNKNOWN", message: "Bad Gateway", status: 502 },
            { logLevel: "warn" }
        );

        expect(result).toBe("throw");
        expect(console.warn).toHaveBeenCalledWith("[API Warning] UNKNOWN: Bad Gateway");
        expect(console.error).not.toHaveBeenCalled();
    });

    it("silent 레벨이면 콘솔 로그를 남기지 않는다", () => {
        const result = handleApiError(
            { error_code: "UNKNOWN", message: "Bad Gateway", status: 502 },
            { logLevel: "silent" }
        );

        expect(result).toBe("throw");
        expect(console.warn).not.toHaveBeenCalled();
        expect(console.error).not.toHaveBeenCalled();
    });
});
