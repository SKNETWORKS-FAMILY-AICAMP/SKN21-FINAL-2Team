// src/services/api.ts

const API_URL = process.env.NEXT_PUBLIC_API_URL || '/api';

const safeLocalGet = (key: string) => (typeof window !== "undefined" ? localStorage.getItem(key) : null);

export interface UserProfile {
    id: number;
    email: string;
    name?: string | null;
    nickname?: string | null;
    gender?: string | null;
    birthday?: string | null;

    // Survey Prefers
    plan_prefer_id?: number | null;
    member_prefer_id?: number | null;
    transport_prefer_id?: number | null;
    age_prefer_id?: number | null;
    vibe_prefer_id?: number | null;

    // Content Prefers
    movie_prefer_id?: number | null;
    drama_prefer_id?: number | null;
    variety_prefer_id?: number | null;

    country_code?: string | null;
    is_join?: boolean | null;
    is_prefer?: boolean | null;
}

export interface PreferItem {
    id: number;
    category?: string | null;
    type?: string | null;
    value?: string | null;
    image_path?: string | null;
}

export const getPostLoginPath = (user: UserProfile): string => {
    if (!user.is_join) return "/signup/profile";
    if (!user.is_prefer) return "/survey";
    return "/chatbot";
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
    if (!res.ok) throw new Error('Refresh failed');
    const data = await res.json();
    if (typeof window !== "undefined") {
        localStorage.setItem('access_token', data.access_token);
        if (data.refresh_token) {
            localStorage.setItem('refresh_token', data.refresh_token);
        }
    }
    return data.access_token as string;
};

type FetchOpts = {
    method?: string;
    body?: any;
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
    if (res.status === 401 || res.status === 400) {
        try {
            await refreshAccessToken();
            res = await doFetch();
        } catch {
            throw new Error('Unauthorized');
        }
    }
    if (!res.ok) {
        const text = await res.text();
        throw new Error(text || 'Request failed');
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

export const fetchCurrentUser = async (): Promise<UserProfile> => {
    const response = await fetchWithAuth(`${API_URL}/users/me`, { cache: 'no-store' });
    return response.json();
};

export const fetchPrefers = async (preferType?: string): Promise<PreferItem[]> => {
    const qs = preferType ? `?type=${encodeURIComponent(preferType)}` : "";
    const response = await fetchWithAuth(`${API_URL}/prefers${qs}`);
    return response.json();
};

export const updateCurrentUser = async (payload: Partial<UserProfile>): Promise<UserProfile> => {
    const response = await fetchWithAuth(`${API_URL}/users/me`, { method: 'PATCH', body: payload });
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
