export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(path, {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(options.headers ?? {})
    },
    ...options
  });
  const text = await response.text();
  const body = text ? JSON.parse(text) : null;
  if (!response.ok) {
    const message = body?.detail ?? `Request failed with HTTP ${response.status}`;
    throw new Error(Array.isArray(message) ? message[0]?.msg ?? "Request failed" : message);
  }
  return body as T;
}
