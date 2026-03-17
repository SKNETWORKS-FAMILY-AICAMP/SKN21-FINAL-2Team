import { NextRequest, NextResponse } from 'next/server';

export async function POST(
    req: NextRequest,
    { params }: { params: Promise<{ roomId: string }> }
) {
    const { roomId } = await params;
    console.log(`[STREAM_ROUTE] ask/stream called for roomId=${roomId}`);
    const backendBase = process.env.NEXT_PUBLIC_API_URL?.startsWith('http')
        ? process.env.NEXT_PUBLIC_API_URL
        : 'http://backend:8000/api';

    const authorization = req.headers.get('Authorization');
    const body = await req.text();

    const upstream = await fetch(`${backendBase}/chat/rooms/${roomId}/ask/stream`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            ...(authorization ? { Authorization: authorization } : {}),
        },
        body,
        // @ts-expect-error — Node.js fetch duplex option
        duplex: 'half',
    });

    if (!upstream.ok) {
        return NextResponse.json(
            { error: 'Backend error' },
            { status: upstream.status }
        );
    }

    return new Response(upstream.body, {
        status: upstream.status,
        headers: {
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache, no-transform',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no',
        },
    });
}
