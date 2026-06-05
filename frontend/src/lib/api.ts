let API_BASE_URL = "http://localhost:8000";

if (typeof window !== "undefined") {
  const envApiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  try {
    const url = new URL(envApiUrl);
    if (url.hostname === "localhost" || url.hostname === "127.0.0.1") {
      const currentHost = window.location.hostname;
      if (currentHost !== "localhost" && currentHost !== "127.0.0.1") {
        url.hostname = currentHost;
        API_BASE_URL = url.origin;
      } else {
        API_BASE_URL = envApiUrl;
      }
    } else {
      API_BASE_URL = envApiUrl;
    }
  } catch {
    API_BASE_URL = envApiUrl;
  }
} else {
  API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
}

export { API_BASE_URL };

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
      } catch {}
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
