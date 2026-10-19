import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  const apiBase = (process.env.CRICKO_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
  let body: { question?: string };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ detail: "Send a valid JSON question." }, { status: 400 });
  }
  try {
    const response = await fetch(new URL("/query", apiBase), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: body.question }),
      cache: "no-store",
      signal: AbortSignal.timeout(20000),
    });
    const payload = await response.json();
    return NextResponse.json(payload, { status: response.status });
  } catch {
    return NextResponse.json({ detail: "CRICKO API is unreachable. Check the Render service and CRICKO_API_URL in Vercel." }, { status: 503 });
  }
}
