import { apiClient, API_BASE_URL } from '@/lib/api';

describe('apiClient', () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    jest.clearAllMocks();
    global.fetch = jest.fn();
  });

  afterAll(() => {
    global.fetch = originalFetch;
  });

  it('performs GET request successfully', async () => {
    const mockData = { success: true };
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockData),
    });

    const res = await apiClient.get('/test');
    expect(res).toEqual(mockData);
    expect(global.fetch).toHaveBeenCalledWith(`${API_BASE_URL}/test`);
  });

  it('performs POST request successfully', async () => {
    const mockData = { id: 1 };
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockData),
    });

    const res = await apiClient.post('/test', { foo: 'bar' });
    expect(res).toEqual(mockData);
    expect(global.fetch).toHaveBeenCalledWith(`${API_BASE_URL}/test`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ foo: 'bar' }),
    });
  });

  it('performs PUT request successfully', async () => {
    const mockData = { updated: true };
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockData),
    });

    const res = await apiClient.put('/test', { foo: 'bar' });
    expect(res).toEqual(mockData);
    expect(global.fetch).toHaveBeenCalledWith(`${API_BASE_URL}/test`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ foo: 'bar' }),
    });
  });

  it('performs DELETE request successfully', async () => {
    const mockData = { deleted: true };
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockData),
    });

    const res = await apiClient.delete('/test');
    expect(res).toEqual(mockData);
    expect(global.fetch).toHaveBeenCalledWith(`${API_BASE_URL}/test`, {
      method: 'DELETE',
    });
  });

  it('throws error when response is not ok and contains detail message', async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: false,
      json: () => Promise.resolve({ detail: 'Some API error' }),
    });

    await expect(apiClient.get('/test')).rejects.toThrow('Some API error');
  });

  it('throws error when response is not ok and contains detail object', async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: false,
      json: () => Promise.resolve({ detail: { error: 'object' } }),
    });

    await expect(apiClient.get('/test')).rejects.toThrow('{"error":"object"}');
  });

  it('throws error when response is not ok and contains message field', async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: false,
      json: () => Promise.resolve({ message: 'Error message' }),
    });

    await expect(apiClient.get('/test')).rejects.toThrow('Error message');
  });

  it('falls back to res.text() if JSON parsing fails', async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: false,
      json: () => Promise.reject(new Error('JSON parse error')),
      text: () => Promise.resolve('Fallback text error'),
    });

    await expect(apiClient.get('/test')).rejects.toThrow('Fallback text error');
  });

  it('falls back to default error if JSON and text parsing fail', async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: false,
      json: () => Promise.reject(new Error('JSON parse error')),
      text: () => Promise.reject(new Error('Text parse error')),
    });

    await expect(apiClient.get('/test')).rejects.toThrow('API Request failed');
  });
});
