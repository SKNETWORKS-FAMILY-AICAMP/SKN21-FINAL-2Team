// src/services/api.ts

const API_URL = '/api';

export const sendChatMessage = async (
    message: string,
    image?: string | null,
    location?: string | null
): Promise<string> => {
    try {
        const body: any = { message };
        if (image) body.image = image;
        if (location) body.location = location;

        const response = await fetch(`${API_URL}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(body),
        });

        if (!response.ok) {
            throw new Error('네트워크 응답에 문제가 있습니다.');
        }

        const data = await response.json();
        return data.reply;

    } catch (error) {
        console.error("Error sending message:", error);
        return "서버와 연결할 수 없습니다.";
    }
};