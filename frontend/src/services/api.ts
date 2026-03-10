// src/services/api.ts

import { decodeJwt } from 'jose';
import { parseApiError, handleApiError, clearAuth } from './errorHandler';

const API_URL = process.env.NEXT_PUBLIC_API_URL || '/api';

const safeLocalGet = (key: string) => (typeof window !== "undefined" ? localStorage.getItem(key) : null);

export interface UserProfile {
    id: number;
    email: string;
    name?: string | null;
    nickname?: string | null;
    profile_picture?: string | null;
    gender?: string | null;
    birthday?: string | null;

    // Survey Prefers (선택한 값 문자열 직접 저장)
    plan_prefer?: string | null;
    vibe_prefer?: string | null;
    places_prefer?: string | null;
    extra_prefer1?: string | null;
    extra_prefer2?: string | null;
    extra_prefer3?: string | null;

    country_code?: string | null;
    is_join?: boolean | null;
    is_prefer?: boolean | null;
}

export interface PreferItem {
    type: string;
    value: string;
}

export const getPostLoginPath = (user: UserProfile): string => {
    if (!user.is_join) return "/signup/profile";
    if (!user.is_prefer) return "/survey";
    // [Feature] 로그인/가입 완료 후 항상 /explore(Home: Your Choices, Hot Places, Content)로 이동
    return "/explore";
};

const getAuthHeaders = (): HeadersInit => {
    const token = safeLocalGet('access_token');
    return token ? {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
    } : {
        'Content-Type': 'application/json'
    };
};

export type RoleType = 'human' | 'ai';

export interface ChatMessage {
    id: number;
    room_id: number;
    message: string;
    role: RoleType;
    latitude?: number;
    longitude?: number;
    image_path?: string | null;
    created_at: string;
    places?: ChatPlaceItem[];
}

export interface ChatPlaceItem {
    id: number;
    place_id?: number;
    name?: string | null;
    category?: string | null;
    adress?: string | null;
    image_path?: string | null;
    longitude?: number;
    latitude?: number;
    map_url?: string | null;
    bookmark_yn?: boolean | null;
}

export interface ChatRoom {
    id: number;
    user_id: number;
    title: string;
    created_at: string;
    bookmark_yn?: boolean | null;
    messages?: ChatMessage[];
}

export interface BookmarkedRoomItem {
    id: number;
    user_id: number;
    title: string;
    created_at: string;
    bookmark_yn: boolean;
    latest_message_preview?: string | null;
}

export interface BookmarkedPlaceItem {
    id: number;
    place_id?: number;
    name?: string | null;
    adress?: string | null;
    image_path?: string | null;
    longitude?: number;
    latitude?: number;
    bookmark_yn?: boolean | null;
    messages_id: number;
    room_id: number;
    room_title: string;
}

export interface TodayRecommendationItem {
    id: string;
    title: string;
    description: string;
    prompt: string;
}

export interface DeleteChatRoomResult {
    ok: boolean;
    room_id: number;
}

export type AutoStartChatMode = "trip_context" | "selected_places" | "combined" | "greeting";

export interface AutoStartTripContextPayload {
    travel_duration: string;
    adult_count: number;
    child_count: number;
}

export interface AutoStartPlaceSeedPayload {
    name?: string | null;
    adress?: string | null;
    place_id?: number;
}

export interface AutoStartChatRoomRequestPayload {
    mode: AutoStartChatMode;
    trip_context?: AutoStartTripContextPayload;
    selected_places?: AutoStartPlaceSeedPayload[];
    save_user_message?: boolean;
}

type StreamCallbacks = {
    onToken: (token: string) => void | Promise<void>;
    onStep: (step: string, status: string) => void | Promise<void>;
    onDone: (fullMessage: string, messageId: number, createdAt: string, roomTitle?: string, places?: ChatPlaceItem[]) => void | Promise<void>;
    onRoomTitle?: (roomTitle: string) => void | Promise<void>;
    onBufferingChange?: (reason: string | null) => void | Promise<void>;
    onError?: (error: string) => void | Promise<void>;
};

export const resolveStreamApiBaseUrl = (
    runtimeLocation?: Pick<Location, "hostname" | "protocol">
): string => {
    const streamApiUrl = process.env.NEXT_PUBLIC_STREAM_API_URL;
    if (streamApiUrl) return streamApiUrl;
    if (typeof window === "undefined") return API_URL;
    if (API_URL !== "/api") return API_URL;

    const { hostname, protocol } = runtimeLocation ?? window.location;
    if (hostname === "localhost" || hostname === "127.0.0.1") {
        return `${protocol}//${hostname}:8000/api`;
    }

    return API_URL;
};

const refreshAccessToken = async () => {
    const refresh_token = safeLocalGet('refresh_token');
    if (!refresh_token) throw new Error('No refresh token');

    const res = await fetch(`${API_URL}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ refresh_token }),
    });
    if (!res.ok) {
        const apiError = await parseApiError(res);
        const action = handleApiError(apiError);
        if (action === 'redirect') throw new Error('Session expired');
        throw new Error(`Refresh failed: ${apiError.error_code}`);
    }
    const data = await res.json();
    if (typeof window !== "undefined") {
        localStorage.setItem('access_token', data.access_token);
        if (data.refresh_token) {
            localStorage.setItem('refresh_token', data.refresh_token);
        }
    }
    return data.access_token as string;
};

/**
 * JWT 토큰 만료 여부를 클라이언트에서 확인 (SECRET_KEY 없이 payload만 디코딩)
 */
const isTokenExpired = (token: string): boolean => {
    try {
        const { exp } = decodeJwt(token);
        if (!exp) return true;
        // 만료 30초 전부터 만료로 간주 (여유 확보)
        return Date.now() >= (Number(exp) - 30) * 1000;
    } catch {
        return true;
    }
};

/**
 * access_token 유효성 검증 → 실패 시 refresh → 둘 다 실패 시 에러
 */
export const verifyAndRefreshToken = async (): Promise<{ valid: boolean; refreshed: boolean }> => {
    const token = safeLocalGet('access_token');
    if (!token) {
        clearAuth();
        throw new Error('No access token');
    }

    // 1) 클라이언트 만료 체크 (빠른 판단)
    if (!isTokenExpired(token)) {
        try {
            const res = await fetch(`${API_URL}/auth/verify`, {
                headers: { 'Authorization': `Bearer ${token}` },
                credentials: 'include',
            });
            if (res.ok) return { valid: true, refreshed: false };
        } catch {
            // 네트워크 에러 → refresh 시도로 fallthrough
        }
    }

    // 2) 만료 또는 검증 실패 → refresh 시도
    try {
        await refreshAccessToken();
        return { valid: true, refreshed: true };
    } catch {
        clearAuth();
        throw new Error('Session expired');
    }
};

type FetchOpts = {
    method?: string;
    body?: unknown;
    headers?: HeadersInit;
    cache?: RequestCache;
};

const fetchWithAuth = async (url: string, opts: FetchOpts = {}) => {
    const { method = 'GET', body, headers, cache } = opts;

    const doFetch = async () => fetch(url, {
        method,
        headers: { ...getAuthHeaders(), ...headers },
        credentials: 'include',
        body: body ? JSON.stringify(body) : undefined,
        cache,
    });

    let res = await doFetch();
    if (!res.ok) {
        const apiError = await parseApiError(res);
        const action = handleApiError(apiError);

        if (action === 'retry') {
            // 토큰 refresh 후 재시도
            try {
                await refreshAccessToken();
                res = await doFetch();
            } catch {
                throw new Error('Unauthorized');
            }
        } else if (action === 'redirect') {
            throw new Error('Session expired');
        } else {
            throw new Error(apiError.message || 'Request failed');
        }
    }
    return res;
};

const parseLocationToCoords = (location?: string | null): { latitude: number; longitude: number } => {
    if (!location) return { latitude: 0, longitude: 0 };
    const parts = location.split(',');
    if (parts.length < 2) return { latitude: 0, longitude: 0 };

    const parsedLat = parseFloat(parts[0].trim());
    const parsedLng = parseFloat(parts[1].trim());
    return {
        latitude: Number.isFinite(parsedLat) ? parsedLat : 0,
        longitude: Number.isFinite(parsedLng) ? parsedLng : 0,
    };
};

const buildChatRequestBody = ({
    roomId,
    message,
    image,
    location,
    saveUserMessage,
}: {
    roomId: number;
    message: string;
    image?: string | null;
    location?: string | null;
    saveUserMessage?: boolean;
}) => {
    const { latitude, longitude } = parseLocationToCoords(location);
    return {
        room_id: roomId,
        message,
        image_path: image,
        latitude,
        longitude,
        role: 'human' as const,
        ...(typeof saveUserMessage === "boolean" ? { save_user_message: saveUserMessage } : {}),
    };
};

export const createRoom = async (title: string): Promise<ChatRoom> => {
    const response = await fetchWithAuth(`${API_URL}/chat/rooms`, { method: 'POST', body: { title } });
    return response.json();
};

export const fetchRooms = async (): Promise<ChatRoom[]> => {
    const response = await fetchWithAuth(`${API_URL}/chat/rooms`);
    return response.json();
};

export const fetchRoom = async (roomId: number): Promise<ChatRoom> => {
    const response = await fetchWithAuth(`${API_URL}/chat/rooms/${roomId}`);
    return response.json();
};

export const deleteRoom = async (roomId: number): Promise<DeleteChatRoomResult> => {
    const response = await fetchWithAuth(`${API_URL}/chat/rooms/${roomId}`, {
        method: "DELETE",
    });
    return response.json();
};

export const updateRoomBookmark = async (roomId: number, bookmark: boolean): Promise<ChatRoom> => {
    const response = await fetchWithAuth(`${API_URL}/chat/rooms/${roomId}/bookmark?bookmark=${bookmark}`, {
        method: 'PATCH'
    });
    return response.json();
};

export const fetchBookmarkedRooms = async (): Promise<BookmarkedRoomItem[]> => {
    const response = await fetchWithAuth(`${API_URL}/chat/bookmarks/rooms`);
    return response.json();
};

export const fetchBookmarkedPlaces = async (): Promise<BookmarkedPlaceItem[]> => {
    const response = await fetchWithAuth(`${API_URL}/chat/bookmarks/places`);
    return response.json();
};

export const fetchTodayRecommendations = async (): Promise<TodayRecommendationItem[]> => {
    const response = await fetchWithAuth(`${API_URL}/chat/recommendations/today`);
    return response.json();
};

export const sendChatMessage = async (
    roomId: number,
    message: string,
    image?: string | null,
    location?: string | null
): Promise<ChatMessage> => {
    const body = buildChatRequestBody({ roomId, message, image, location });

    const response = await fetchWithAuth(`${API_URL}/chat/rooms/${roomId}/ask`, { method: 'POST', body });
    return response.json();
};

export const sendChatMessageStream = async (
    roomId: number,
    message: string,
    callbacks: StreamCallbacks,
    image?: string | null,
    location?: string | null,
    options?: {
        saveUserMessage?: boolean;
        signal?: AbortSignal;
    }
): Promise<void> => {
    const body = buildChatRequestBody({
        roomId,
        message,
        image,
        location,
        saveUserMessage: options?.saveUserMessage ?? true,
    });
    const streamApiBaseUrl = resolveStreamApiBaseUrl();

    const streamFetch = async () => {
        const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;
        const headers: HeadersInit = {
            'Content-Type': 'application/json',
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
        };

        return fetch(`${streamApiBaseUrl}/chat/rooms/${roomId}/ask/stream`, {
            method: 'POST',
            headers,
            credentials: 'include',
            signal: options?.signal,
            body: JSON.stringify(body),
        });
    };
    return streamSseRequest(streamFetch, callbacks);
};

const streamSseRequest = async (
    streamFetch: () => Promise<Response>,
    callbacks: StreamCallbacks
): Promise<void> => {
    const yieldToUI = async () => {
        if (typeof window === "undefined") return;
        await new Promise<void>((resolve) => window.setTimeout(resolve, 16));
    };

    let response = await streamFetch();
    if (!response.ok) {
        const apiError = await parseApiError(response);
        const action = handleApiError(apiError);

        if (action === 'retry') {
            try {
                await refreshAccessToken();
                response = await streamFetch();
            } catch {
                await callbacks.onError?.('Session expired');
                return;
            }
        } else if (action === 'redirect') {
            await callbacks.onError?.('Session expired');
            return;
        } else {
            await callbacks.onError?.(apiError.message || response.statusText);
            return;
        }
    }

    if (!response.ok) {
        await callbacks.onError?.(response.statusText);
        return;
    }

    const reader = response.body?.getReader();
    if (!reader) return;

    const decoder = new TextDecoder();
    let buffer = '';
    let receivedDone = false;
    let lastFullMessage = '';
    let lastMessageId = 0;
    let lastCreatedAt = '';
    let lastRoomTitle: string | undefined;
    let lastPlaces: ChatPlaceItem[] | undefined;
    const handleEvent = async (rawEvent: string) => {
        const lines = rawEvent
            .split('\n')
            .filter((line) => line.startsWith('data: '))
            .map((line) => line.slice(6));
        if (lines.length === 0) return;
        const payload = lines.join('\n');
        try {
            const data = JSON.parse(payload);
            if (data.token) {
                await callbacks.onToken(data.token);
                await yieldToUI();
            } else if (data.step) {
                await callbacks.onStep(data.step, data.status);
                await yieldToUI();
            } else if ("buffering" in data) {
                await callbacks.onBufferingChange?.(data.buffering ?? null);
            } else if (data.room_title && !data.done) {
                await callbacks.onRoomTitle?.(data.room_title);
            } else if (data.done) {
                receivedDone = true;
                lastFullMessage = data.full_message || '';
                lastMessageId = Number.isFinite(Number(data.message_id)) ? Number(data.message_id) : 0;
                lastCreatedAt = data.created_at || '';
                lastRoomTitle = data.room_title;
                lastPlaces = data.places;
                await callbacks.onDone(lastFullMessage, lastMessageId, lastCreatedAt, lastRoomTitle, lastPlaces);
            }
        } catch {
            // JSON 파싱 실패 무시
        }
    };

    while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // SSE 이벤트 단위 파싱 (event delimiter: \n\n)
        const events = buffer.split('\n\n');
        buffer = events.pop() || '';

        for (const rawEvent of events) {
            await handleEvent(rawEvent);
        }
    }

    if (buffer.trim()) {
        await handleEvent(buffer);
    }

    // 네트워크 경계로 done 이벤트가 누락/파싱 실패한 경우를 대비한 최종 보정
    if (!receivedDone && (lastFullMessage || lastMessageId > 0)) {
        await callbacks.onDone(lastFullMessage, lastMessageId, lastCreatedAt, lastRoomTitle, lastPlaces);
    }
};

export const sendAutoStartChatRoomStream = async (
    roomId: number,
    payload: AutoStartChatRoomRequestPayload,
    callbacks: StreamCallbacks
): Promise<void> => {
    const body: AutoStartChatRoomRequestPayload = {
        ...payload,
        save_user_message: payload.save_user_message ?? false,
    };
    const streamApiBaseUrl = resolveStreamApiBaseUrl();

    const streamFetch = async () => {
        const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;
        const headers: HeadersInit = {
            'Content-Type': 'application/json',
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
        };
        return fetch(`${streamApiBaseUrl}/chat/rooms/${roomId}/autostart/stream`, {
            method: 'POST',
            headers,
            credentials: 'include',
            body: JSON.stringify(body),
        });
    };

    return streamSseRequest(streamFetch, callbacks);
};

export const fetchCurrentUser = async (): Promise<UserProfile> => {
    const response = await fetchWithAuth(`${API_URL}/users/me`, { cache: 'no-store' });
    return response.json();
};

export const fetchPrefers = async (preferType?: string): Promise<PreferItem[]> => {
    const qs = preferType ? `?prefer_type=${encodeURIComponent(preferType)}` : "";
    const response = await fetchWithAuth(`${API_URL}/prefers${qs}`);
    return response.json();
};

export const updateCurrentUser = async (payload: Partial<UserProfile>): Promise<UserProfile> => {
    const response = await fetchWithAuth(`${API_URL}/users/me`, { method: 'PATCH', body: payload });
    return response.json();
};

export const resetCurrentUserProfilePictureToGoogle = async (): Promise<UserProfile> => {
    const response = await fetchWithAuth(`${API_URL}/users/me/reset-profile-picture`, { method: "POST" });
    return response.json();
};

export const deactivateCurrentUser = async (): Promise<{ ok: boolean }> => {
    const response = await fetchWithAuth(`${API_URL}/users/me/deactivate`, { method: "POST" });
    if (!response.ok) {
        const apiError = await parseApiError(response);
        throw new Error(apiError.message || `Deactivate failed: ${apiError.error_code}`);
    }
    return response.json();
};

export const submitSurvey = async (answers: Record<string, string>): Promise<UserProfile> => {
    const response = await fetchWithAuth(`${API_URL}/prefers`, { method: 'PATCH', body: answers });
    return response.json();
};

export interface HotPlace {
    id: number;
    name: string;
    adress?: string | null;
    feature?: string | null;
    tag1?: string | null;
    tag2?: string | null;
    image_path?: string | null;
}

export const fetchHotPlaces = async (limit = 3): Promise<HotPlace[]> => {
    const response = await fetchWithAuth(`${API_URL}/explore/hot-places?limit=${limit}`);
    return response.json();
};

export interface Country {
    code: string;
    name: string;
}

export const fetchCountries = async (): Promise<Country[]> => {
    const response = await fetchWithAuth(`${API_URL}/common/countries`);
    return response.json();
};

export interface ReservationRecord {
    id: number;
    user_id: number;
    category?: string | null;
    name?: string | null;
    date?: string | null;
    image_path?: string | null;
    created_at?: string | null;
    updated_at?: string | null;
}

export type ReservationPayload = {
    category?: string | null;
    name?: string | null;
    date?: string | null;
    image_path?: string | null;
};

export interface DiaryLinkedRoom {
    id: number;
    title: string;
    created_at: string;
}

export interface DiaryLinkedPlace {
    id: number;
    chat_place_id?: number | null;
    place_id?: number | null;
    name?: string | null;
    adress?: string | null;
    image_path?: string | null;
    longitude?: number | null;
    latitude?: number | null;
    created_at?: string | null;
}

export interface DiaryLinkedPlaceInput {
    name?: string | null;
    adress: string;
    image_path?: string | null;
    longitude: number;
    latitude: number;
    place_id?: number | null;
    chat_place_id?: number | null;
}

export interface DiaryListItem {
    id: number;
    title: string;
    content: string;
    entry_date: string;
    cover_image_path?: string | null;
    linked_places_count: number;
    created_at?: string | null;
    updated_at?: string | null;
}

export interface DiaryDetail extends DiaryListItem {
    user_id: number;
    linked_chat_room?: DiaryLinkedRoom | null;
    linked_places: DiaryLinkedPlace[];
}

export type DiaryPayload = {
    title: string;
    content: string;
    entry_date: string;
    cover_image_path?: string | null;
    linked_places?: DiaryLinkedPlaceInput[];
};

export interface DiaryPlaceSearchResult {
    name?: string | null;
    adress: string;
    latitude: number;
    longitude: number;
}

export const fetchReservations = async (): Promise<ReservationRecord[]> => {
    const response = await fetchWithAuth(`${API_URL}/reservations`);
    return response.json();
};

export const fetchDiaries = async (params?: {
    query?: string;
    date_from?: string;
    date_to?: string;
}): Promise<DiaryListItem[]> => {
    const qs = new URLSearchParams();
    if (params?.query) qs.set("query", params.query);
    if (params?.date_from) qs.set("date_from", params.date_from);
    if (params?.date_to) qs.set("date_to", params.date_to);
    const suffix = qs.toString() ? `?${qs.toString()}` : "";
    const response = await fetchWithAuth(`${API_URL}/diaries${suffix}`);
    return response.json();
};

export const fetchDiary = async (diaryId: number): Promise<DiaryDetail> => {
    const response = await fetchWithAuth(`${API_URL}/diaries/${diaryId}`);
    return response.json();
};

export const createDiary = async (payload: DiaryPayload): Promise<DiaryDetail> => {
    const response = await fetchWithAuth(`${API_URL}/diaries`, { method: "POST", body: payload });
    return response.json();
};

export const updateDiary = async (diaryId: number, payload: Partial<DiaryPayload>): Promise<DiaryDetail> => {
    const response = await fetchWithAuth(`${API_URL}/diaries/${diaryId}`, { method: "PATCH", body: payload });
    return response.json();
};

export const deleteDiary = async (diaryId: number): Promise<{ ok: boolean }> => {
    const response = await fetchWithAuth(`${API_URL}/diaries/${diaryId}`, { method: "DELETE" });
    return response.json();
};

export const searchDiaryPlaces = async (query: string): Promise<DiaryPlaceSearchResult[]> => {
    const qs = new URLSearchParams({ query });
    const response = await fetchWithAuth(`${API_URL}/diaries/place-search?${qs.toString()}`);
    return response.json();
};

export const reverseGeocodeDiaryPlace = async (latitude: number, longitude: number): Promise<DiaryPlaceSearchResult> => {
    const qs = new URLSearchParams({
        latitude: latitude.toString(),
        longitude: longitude.toString(),
    });
    const response = await fetchWithAuth(`${API_URL}/diaries/reverse-geocode?${qs.toString()}`);
    return response.json();
};

export const createReservation = async (payload: ReservationPayload): Promise<ReservationRecord> => {
    const response = await fetchWithAuth(`${API_URL}/reservations`, { method: "POST", body: payload });
    return response.json();
};

export const updateReservation = async (reservationId: number, payload: ReservationPayload): Promise<ReservationRecord> => {
    const response = await fetchWithAuth(`${API_URL}/reservations/${reservationId}`, { method: "PATCH", body: payload });
    return response.json();
};

export const deleteReservation = async (reservationId: number): Promise<{ ok: boolean }> => {
    const response = await fetchWithAuth(`${API_URL}/reservations/${reservationId}`, { method: "DELETE" });
    return response.json();
};

export interface CategoryPlaceItem {
    contentid: string;
    title: string;
    address: string;
    image_url: string;
    score: number;
    description: string;
    start_date?: string;
    end_date?: string;
}

export const fetchCategoryPlaces = async (userPrefs: string): Promise<Record<string, CategoryPlaceItem[]>> => {
    const response = await fetchWithAuth(`${API_URL}/explore/category-places`, {
        method: 'POST',
        body: { user_prefs: userPrefs }
    });
    return response.json();
};

export const fetchRandomExplorePlaces = async (
    categories?: string,
    limit?: number
): Promise<Record<string, CategoryPlaceItem[]>> => {
    let url = `${API_URL}/explore/random-places`;
    const params = new URLSearchParams();
    if (categories) params.append("categories", categories);
    if (limit) params.append("limit", limit.toString());

    if (params.toString()) {
        url += `?${params.toString()}`;
    }

    const response = await fetchWithAuth(url);
    return response.json();
};

export const logoutApi = async () => {
    try {
        await fetch(`${API_URL}/auth/logout`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
        });
    } catch (e) {
        console.error("Logout API failed:", e);
    }
};

export const updatePlaceBookmark = async (placeId: number, bookmark: boolean): Promise<ChatPlaceItem> => {
    const response = await fetchWithAuth(`${API_URL}/chat/places/${placeId}/bookmark?bookmark=${bookmark}`, {
        method: 'PATCH'
    });
    return response.json();
};

export const uploadImageDataUrl = async (dataUrl: string, folder = "misc"): Promise<string> => {
    if (!dataUrl || !dataUrl.startsWith("data:image/")) return dataUrl;
    const response = await fetchWithAuth(`${API_URL}/common/upload-image`, {
        method: "POST",
        body: { data_url: dataUrl, folder },
    });
    const data = await response.json();
    return data.image_path as string;
};
