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
    latitude?: number | null;
    longitude?: number | null;
    image_path?: string | null;
    bookmark_yn?: boolean | null;
    created_at: string;
}

export interface ChatRoom {
    id: number;
    user_id: number;
    title: string;
    created_at: string;
    messages?: ChatMessage[];
}

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

export const sendChatMessage = async (
    roomId: number,
    message: string,
    image?: string | null,
    location?: string | null
): Promise<ChatMessage> => {
    let latitude = null;
    let longitude = null;

    if (location) {
        const parts = location.split(',');
        if (parts.length >= 2) {
            latitude = parseFloat(parts[0].trim());
            longitude = parseFloat(parts[1].trim());
        }
    }

    const body = {
        room_id: roomId,
        message,
        image_path: image,
        latitude,
        longitude,
        role: 'human'
    };

    const response = await fetchWithAuth(`${API_URL}/chat/rooms/${roomId}/ask`, { method: 'POST', body });
    return response.json();
};

export const sendChatMessageStream = async (
    roomId: number,
    message: string,
    callbacks: {
        onToken: (token: string) => void;
        onStep: (step: string, status: string) => void;
        onDone: (fullMessage: string, messageId: number, createdAt: string, roomTitle?: string) => void;
        onRoomTitle?: (roomTitle: string) => void;
        onError?: (error: string) => void;
    },
    image?: string | null,
    location?: string | null
): Promise<void> => {
    let latitude = null;
    let longitude = null;

    if (location) {
        const parts = location.split(',');
        if (parts.length >= 2) {
            latitude = parseFloat(parts[0].trim());
            longitude = parseFloat(parts[1].trim());
        }
    }

    const body = {
        room_id: roomId,
        message,
        image_path: image,
        latitude,
        longitude,
        role: 'human',
    };

    const streamFetch = async () => {
        const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;
        const headers: HeadersInit = {
            'Content-Type': 'application/json',
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
        };

        return fetch(`${API_URL}/chat/rooms/${roomId}/ask/stream`, {
            method: 'POST',
            headers,
            credentials: 'include',
            body: JSON.stringify(body),
        });
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
                callbacks.onError?.('Session expired');
                return;
            }
        } else if (action === 'redirect') {
            callbacks.onError?.('Session expired');
            return;
        } else {
            callbacks.onError?.(apiError.message || response.statusText);
            return;
        }
    }

    if (!response.ok) {
        callbacks.onError?.(response.statusText);
        return;
    }

    const reader = response.body?.getReader();
    if (!reader) return;

    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // SSE 라인 파싱
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
            if (!line.startsWith('data: ')) continue;
            try {
                const data = JSON.parse(line.slice(6));
                if (data.token) {
                    callbacks.onToken(data.token);
                } else if (data.step) {
                    callbacks.onStep(data.step, data.status);
                } else if (data.room_title && !data.done) {
                    // Intent 완료 직후 즉시 전송되는 제목 업데이트
                    callbacks.onRoomTitle?.(data.room_title);
                } else if (data.done) {
                    callbacks.onDone(data.full_message || '', data.message_id, data.created_at, data.room_title);
                }
            } catch {
                // JSON 파싱 실패 무시
            }
        }
    }
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
    const response = await fetchWithAuth(`${API_URL}/hot-places?limit=${limit}`);
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

export interface CategoryPlaceItem {
    contentid: string;
    title: string;
    address: string;
    image_url: string;
    score: number;
    description: string;
}

export const fetchCategoryPlaces = async (userPrefs: string): Promise<Record<string, CategoryPlaceItem[]>> => {
    const response = await fetchWithAuth(`${API_URL}/explore/category-places`, {
        method: 'POST',
        body: { user_prefs: userPrefs }
    });
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
