describe("resolveStreamApiBaseUrl", () => {
    afterEach(() => {
        delete process.env.NEXT_PUBLIC_STREAM_API_URL;
        delete process.env.NEXT_PUBLIC_API_URL;
        jest.resetModules();
    });

    it("브라우저에서 절대 API URL이 설정되어 있어도 same-origin /api를 반환한다", async () => {
        process.env.NEXT_PUBLIC_API_URL = "https://api.example.com/api";

        const { resolveStreamApiBaseUrl } = await import("../src/services/api");

        expect(
            resolveStreamApiBaseUrl({
                hostname: "app.example.com",
                protocol: "https:",
            })
        ).toBe("/api");
    });

    it("브라우저에서 API_URL이 /api면 localhost여도 /api를 유지한다", async () => {
        process.env.NEXT_PUBLIC_API_URL = "/api";

        const { resolveStreamApiBaseUrl } = await import("../src/services/api");

        expect(
            resolveStreamApiBaseUrl({
                hostname: "localhost",
                protocol: "http:",
            })
        ).toBe("/api");
    });

    it("NEXT_PUBLIC_STREAM_API_URL이 있으면 해당 값을 우선 사용한다", async () => {
        process.env.NEXT_PUBLIC_API_URL = "https://api.example.com/api";
        process.env.NEXT_PUBLIC_STREAM_API_URL = "https://stream.example.com/api";

        const { resolveStreamApiBaseUrl } = await import("../src/services/api");

        expect(
            resolveStreamApiBaseUrl({
                hostname: "app.example.com",
                protocol: "https:",
            })
        ).toBe("https://stream.example.com/api");
    });
});
