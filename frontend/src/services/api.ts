// src/services/api.ts

const API_URL = process.env.NEXT_PUBLIC_API_URL;

export const sendChatMessage = async (message: string): Promise<string> => {
    try {
        const response = await fetch(`${API_URL}/api/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json', // 백엔드에게 JSON임을 알림
            },
            body: JSON.stringify({ message }), // 객체를 문자열로 변환
        });

        if (!response.ok) {
            throw new Error('네트워크 응답에 문제가 있습니다.');
        }

        const data = await response.json(); // 응답 문자열을 다시 JSON 객체로 변환
        return data.reply; // FastAPI가 줄 { "reply": "안녕!" } 에서 reply 추출

    } catch (error) {
        console.error("Error sending message:", error);
        return "서버와 연결할 수 없습니다.";
    }
};