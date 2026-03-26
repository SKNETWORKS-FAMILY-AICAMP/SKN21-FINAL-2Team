const S3_BASE = (process.env.NEXT_PUBLIC_S3_PUBLIC_BASE_URL || "").replace(/\/$/, "");

/** 장소 이미지를 불러올 수 없을 때 보여주는 로컬 기본 이미지 */
export const PLACE_PLACEHOLDER = "/image/place-placeholder.svg";

/**
 * 저장된 image path를 표시 가능한 URL로 변환.
 * - http/https/data:image → 그대로 반환
 * - 상대 path → NEXT_PUBLIC_S3_PUBLIC_BASE_URL + path 또는 /api/static/ + path
 */
export function resolveImageUrl(value: string | null | undefined): string {
    const text = (value || "").trim();
    if (!text) return "";
    if (
        text.startsWith("http://") ||
        text.startsWith("https://") ||
        text.startsWith("data:image") ||
        text.startsWith("/api/static/")
    ) {
        return text;
    }
    if (S3_BASE) {
        return `${S3_BASE}/${text.replace(/^\//, "")}`;
    }
    return `/api/static/${text.replace(/^\//, "")}`;
}
