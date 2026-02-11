// src/services/api.ts

const API_URL = 'http://localhost:8000/api';

const getAuthHeaders = (): HeadersInit => {
    const token = localStorage.getItem('access_token');
    return token ? {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
    } : {
        'Content-Type': 'application/json'
    };
};

const getRoomId = async (): Promise<number> => {
    let roomId = localStorage.getItem('chat_room_id');
    if (roomId) {
        return parseInt(roomId, 10);
    }

    // Create new chat room
    try {
        const response = await fetch(`${API_URL}/chat/rooms`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ title: 'New Chat' })
        });
        
        if (!response.ok) throw new Error('Failed to create room');

        const data = await response.json();
        localStorage.setItem('chat_room_id', data.id.toString());
        return data.id;
    } catch (error) {
        console.error("Room creation failed:", error);
        throw error;
    }
};

export const sendChatMessage = async (
    message: string,
    image?: string | null,
    location?: string | null
): Promise<string> => {
    try {
        const roomId = await getRoomId();
        console.log('room id:', roomId);

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

        const response = await fetch(`${API_URL}/chat/rooms/${roomId}/ask`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(body),
        });

        if (!response.ok) {
            throw new Error('네트워크 응답에 문제가 있습니다.');
        }

        const data = await response.json();
        // Backend returns ChatMessageResponse { id, message, ... }
        return data.message;

    } catch (error) {
        console.error("Error sending message:", error);
        return "서버와 연결할 수 없습니다.";
    }
};
