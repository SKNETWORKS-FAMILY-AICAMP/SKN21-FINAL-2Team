import { NextResponse } from 'next/server';

export async function POST(req: Request) {
    try {
        const body = await req.json();
        const backendUrl = process.env.BACKEND_URL || 'http://backend:8000';

        const response = await fetch(`${backendUrl}/api/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(body),
        });

        if (!response.ok) {
            return NextResponse.json(
                { error: 'Backend server error' },
                { status: response.status }
            );
        }

        const data = await response.json();
        return NextResponse.json(data);
    } catch (error) {
        console.error('Error proxying to backend:', error);
        return NextResponse.json(
            { error: 'Internal Server Error' },
            { status: 500 }
        );
    }
}
