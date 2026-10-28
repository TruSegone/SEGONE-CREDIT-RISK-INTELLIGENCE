const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/** Fetch JSON and turn unsuccessful HTTP responses into readable UI errors. */
export async function get<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`);
  if (!response.ok) {
    throw new Error(`API request failed (${response.status})`);
  }
  return response.json();
}

/** Submit a JSON request and preserve FastAPI's safe validation detail. */
export async function post<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(
      errorBody.detail || `API request failed (${response.status})`,
    );
  }
  return response.json();
}

/** CSV export is a normal browser download served by the API. */
export const exportUrl = `${API_BASE_URL}/api/v1/portfolio/export`;
