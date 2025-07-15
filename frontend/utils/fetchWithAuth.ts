export async function fetchWithAuth(url: string, token: string, options: RequestInit = {}) {
    const headers = {
      ...options.headers,
      Authorization: `Bearer ${token}`,
    };
  
    const res = await fetch(url, {
      ...options,
      headers,
    });
  
    if (!res.ok) {
      throw new Error(`Request failed: ${res.status}`);
    }
  
    return res.json();
  }
  