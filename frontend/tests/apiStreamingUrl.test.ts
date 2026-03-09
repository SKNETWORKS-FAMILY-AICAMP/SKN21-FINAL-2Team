describe("resolveStreamApiBaseUrl", () => {
    const originalEnv = process.env.NEXT_PUBLIC_STREAM_API_URL;
    const originalApiUrl = process.env.NEXT_PUBLIC_API_URL;

    afterEach(() => {
        if (originalEnv === undefined) {
            delete process.env.NEXT_PUBLIC_STREAM_API_URL;
        } else {
            process.env.NEXT_PUBLIC_STREAM_API_URL = originalEnv;
        }

        if (originalApiUrl === undefined) {
            delete process.env.NEXT_PUBLIC_API_URL;
        } else {
            process.env.NEXT_PUBLIC_API_URL = originalApiUrl;
        }

        jest.resetModules();
    });

    it("기본값은 현재 API_URL 설정을 그대로 사용한다", () => {
        delete process.env.NEXT_PUBLIC_STREAM_API_URL;
        process.env.NEXT_PUBLIC_API_URL = "/api";
        jest.resetModules();
        const { resolveStreamApiBaseUrl } = require("../src/services/api");

        expect(
            resolveStreamApiBaseUrl({ hostname: "localhost", protocol: "http:" })
        ).toBe("/api");
    });

    it("스트리밍 전용 env가 있으면 우선 사용한다", () => {
        process.env.NEXT_PUBLIC_API_URL = "/api";
        process.env.NEXT_PUBLIC_STREAM_API_URL = "https://api.example.com";
        jest.resetModules();
        const { resolveStreamApiBaseUrl } = require("../src/services/api");

        expect(
            resolveStreamApiBaseUrl({ hostname: "localhost", protocol: "http:" })
        ).toBe("https://api.example.com");
    });
});
