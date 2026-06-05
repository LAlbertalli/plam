export const API_BASE_URL = typeof window !== "undefined"
  ? "/api/v1"
  : `http://localhost:${process.env.PORT || 3000}/api/v1`;

const handleResponse = async (res: Response) => {
  if (!res.ok) {
    let errorDetail = "API Request failed";
    try {
      const data = await res.json();
      if (data && data.detail) {
        errorDetail = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
      } else if (data && data.message) {
        errorDetail = data.message;
      }
    } catch {
      try {
        const text = await res.text();
        if (text) errorDetail = text;
      } catch { }
    }
    throw new Error(errorDetail);
  }
  return res.json();
};

export const apiClient = {
  get: async (endpoint: string) => {
    const res = await fetch(`${API_BASE_URL}${endpoint}`);
    return handleResponse(res);
  },
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  post: async (endpoint: string, data: any) => {
    const res = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return handleResponse(res);
  },
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  put: async (endpoint: string, data: any) => {
    const res = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return handleResponse(res);
  },
  delete: async (endpoint: string) => {
    const res = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: 'DELETE',
    });
    return handleResponse(res);
  }
};
