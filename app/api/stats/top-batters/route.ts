import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const apiBase = (process.env.CRICKO_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
  const incoming = new URL(request.url);
  const target = new URL("/stats/top-batters", apiBase);
  incoming.searchParams.forEach((value, key) => target.searchParams.set(key, value));

  try {
    const response = await fetch(target, { cache: "no-store", signal: AbortSignal.timeout(8000) });
    const payload = await response.json();
    return NextResponse.json(payload, { status: response.status });
  } catch {
    return NextResponse.json(
      { error: "Cricko statistics API is not connected. Start the FastAPI service and set CRICKO_API_URL if it is hosted elsewhere." },
      { status: 503 },
    );
  }
}
