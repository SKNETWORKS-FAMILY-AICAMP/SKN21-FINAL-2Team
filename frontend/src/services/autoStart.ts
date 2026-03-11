export type PendingAutoStartMode = "greeting" | "trip_context" | "selected_places" | "combined";

export interface StoredTripContext {
    travelDuration: string;
    adultCount: number;
    childCount: number;
}

export interface StoredSelectedPlaceSeed {
    id?: number;
    place_id?: number | null;
    name?: string | null;
    adress?: string | null;
    image_path?: string | null;
    room_id?: number;
}

export interface PendingAutoStartMeta {
    mode: PendingAutoStartMode | null;
    tripContext: StoredTripContext | null;
    selectedPlaces: StoredSelectedPlaceSeed[];
}

const MODE_KEY_PREFIX = "triver:auto-start-mode:";
const STARTED_KEY_PREFIX = "triver:auto-start-started:";
const TRIP_CONTEXT_KEY_PREFIX = "triver:trip-context:";
const SELECTED_PLACES_KEY_PREFIX = "triver:selected-places:";
const LEGACY_GREETING_KEY_PREFIX = "triver:auto-start-greeting:";
const LEGACY_TRIP_STARTED_KEY_PREFIX = "triver:trip-context-started:";
const LEGACY_SELECTED_STARTED_KEY_PREFIX = "triver:selected-places-started:";

const readJson = <T,>(raw: string | null): T | null => {
    if (!raw) return null;
    try {
        return JSON.parse(raw) as T;
    } catch {
        return null;
    }
};

const modeKey = (roomId: number) => `${MODE_KEY_PREFIX}${roomId}`;
const startedKey = (roomId: number) => `${STARTED_KEY_PREFIX}${roomId}`;
const tripContextKey = (roomId: number) => `${TRIP_CONTEXT_KEY_PREFIX}${roomId}`;
const selectedPlacesKey = (roomId: number) => `${SELECTED_PLACES_KEY_PREFIX}${roomId}`;
const legacyGreetingKey = (roomId: number) => `${LEGACY_GREETING_KEY_PREFIX}${roomId}`;
const legacyTripStartedKey = (roomId: number) => `${LEGACY_TRIP_STARTED_KEY_PREFIX}${roomId}`;
const legacySelectedStartedKey = (roomId: number) => `${LEGACY_SELECTED_STARTED_KEY_PREFIX}${roomId}`;

export const clearPendingAutoStartMeta = (roomId: number) => {
    localStorage.removeItem(modeKey(roomId));
    localStorage.removeItem(legacyGreetingKey(roomId));
};

export const clearAutoStartStarted = (roomId: number) => {
    localStorage.removeItem(startedKey(roomId));
    localStorage.removeItem(legacyTripStartedKey(roomId));
    localStorage.removeItem(legacySelectedStartedKey(roomId));
};

export const resetAutoStartRoomState = (roomId: number) => {
    localStorage.removeItem(tripContextKey(roomId));
    localStorage.removeItem(selectedPlacesKey(roomId));
    clearPendingAutoStartMeta(roomId);
    clearAutoStartStarted(roomId);
};

export const setPendingAutoStartMeta = (
    roomId: number,
    payload: {
        mode: PendingAutoStartMode;
        tripContext?: StoredTripContext | null;
        selectedPlaces?: StoredSelectedPlaceSeed[] | null;
    }
) => {
    resetAutoStartRoomState(roomId);
    localStorage.setItem(modeKey(roomId), payload.mode);

    if (payload.tripContext) {
        localStorage.setItem(tripContextKey(roomId), JSON.stringify(payload.tripContext));
    }

    if (payload.selectedPlaces?.length) {
        localStorage.setItem(selectedPlacesKey(roomId), JSON.stringify(payload.selectedPlaces));
    }

    if (payload.mode === "greeting") {
        localStorage.setItem(legacyGreetingKey(roomId), "1");
    }
};

export const readPendingAutoStartMeta = (roomId: number): PendingAutoStartMeta => {
    const tripContext = readJson<StoredTripContext>(localStorage.getItem(tripContextKey(roomId)));
    const selectedPlaces = readJson<StoredSelectedPlaceSeed[]>(localStorage.getItem(selectedPlacesKey(roomId))) || [];
    const explicitMode = localStorage.getItem(modeKey(roomId)) as PendingAutoStartMode | null;

    if (explicitMode) {
        return { mode: explicitMode, tripContext, selectedPlaces };
    }

    if (tripContext && selectedPlaces.length > 0) {
        return { mode: "combined", tripContext, selectedPlaces };
    }
    if (selectedPlaces.length > 0) {
        return { mode: "selected_places", tripContext, selectedPlaces };
    }
    if (tripContext) {
        return { mode: "trip_context", tripContext, selectedPlaces };
    }
    if (localStorage.getItem(legacyGreetingKey(roomId)) === "1") {
        return { mode: "greeting", tripContext, selectedPlaces };
    }

    return { mode: null, tripContext, selectedPlaces };
};

export const hasAutoStartStarted = (roomId: number) => (
    localStorage.getItem(startedKey(roomId)) === "1" ||
    localStorage.getItem(legacyTripStartedKey(roomId)) === "1" ||
    localStorage.getItem(legacySelectedStartedKey(roomId)) === "1"
);

export const markAutoStartStarted = (roomId: number) => {
    localStorage.setItem(startedKey(roomId), "1");
};
