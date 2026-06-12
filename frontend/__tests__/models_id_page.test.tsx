import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import ModelDetailPage from '@/app/models/[id]/page';
import { apiClient } from '@/lib/api';
import React, { Suspense } from 'react';

// Mock the api client
jest.mock('@/lib/api', () => ({
  apiClient: {
    get: jest.fn(),
    post: jest.fn(),
    put: jest.fn(),
    delete: jest.fn(),
  }
}));

// Mock window.confirm and window.alert
const mockConfirm = jest.fn();
Object.defineProperty(window, 'confirm', {
  value: mockConfirm
});

const mockAlert = jest.fn();
Object.defineProperty(window, 'alert', {
  value: mockAlert
});

describe('ModelDetailPage', () => {
  const mockParams = Promise.resolve({ id: 'model-1' });

  const mockModel = {
    id: 'model-1',
    name: 'Qwen-7B',
    hf_repo_id: 'Qwen/Qwen-7B',
    gguf_filename: 'qwen.gguf',
    status: 'stopped',
    ram_required_mb: 8192,
    context_size: 2048,
    llamacpp_version_hash: 'abc',
    local_path: null
  };

  const mockRules = [
    {
      id: 'rule-1',
      model_id: 'model-1',
      name: 'System Rule 1',
      pattern: 'foo',
      replacement: 'bar',
      chain: 'input_chain',
      order: 1,
      is_active: true
    },
    {
      id: 'rule-2',
      model_id: 'model-1',
      name: 'System Rule 2',
      pattern: 'hello',
      replacement: 'world',
      chain: 'input_chain',
      order: 2,
      is_active: false
    }
  ];

  beforeEach(() => {
    jest.clearAllMocks();
    (apiClient.get as jest.Mock).mockImplementation((url: string) => {
      if (url === '/models/model-1') return Promise.resolve(mockModel);
      if (url.startsWith('/proxies')) return Promise.resolve(mockRules);
      return Promise.resolve([]);
    });
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('renders loading state initially', async () => {
    (apiClient.get as jest.Mock).mockReturnValue(new Promise(() => {}));
    render(
      <Suspense fallback={<div>Loading model details...</div>}>
        <ModelDetailPage params={mockParams} />
      </Suspense>
    );
    expect(screen.getByText('Loading model details...')).toBeInTheDocument();
  });

  it('fetches and displays model details and rules', async () => {
    render(
      <Suspense fallback={<div>Loading...</div>}>
        <ModelDetailPage params={mockParams} />
      </Suspense>
    );

    await waitFor(() => {
      expect(screen.getByText('Qwen-7B')).toBeInTheDocument();
      expect(screen.getByText('System Rule 1')).toBeInTheDocument();
    });

    expect(screen.getByText('foo')).toBeInTheDocument();
    expect(screen.getByText('bar')).toBeInTheDocument();
  });

  it('handles API fetch errors gracefully', async () => {
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    (apiClient.get as jest.Mock).mockRejectedValue(new Error('Fetch failed'));
    
    render(
      <Suspense fallback={<div>Loading...</div>}>
        <ModelDetailPage params={mockParams} />
      </Suspense>
    );

    await waitFor(() => {
      expect(consoleSpy).toHaveBeenCalledWith('Failed to fetch model details:', expect.any(Error));
      expect(consoleSpy).toHaveBeenCalledWith('Failed to fetch rules:', expect.any(Error));
    });
    consoleSpy.mockRestore();
  });

  it('deletes a rule when delete is clicked and confirmed', async () => {
    mockConfirm.mockReturnValue(true);
    (apiClient.delete as jest.Mock).mockResolvedValue({});
    
    render(
      <Suspense fallback={<div>Loading...</div>}>
        <ModelDetailPage params={mockParams} />
      </Suspense>
    );

    await waitFor(() => {
      expect(screen.getByText('System Rule 1')).toBeInTheDocument();
    });

    const deleteButtons = screen.getAllByText('Delete');
    fireEvent.click(deleteButtons[0]);
    
    expect(mockConfirm).toHaveBeenCalled();
    await waitFor(() => {
      expect(apiClient.delete).toHaveBeenCalledWith('/proxies/rule-1');
    });
  });

  it('does not delete rule if not confirmed', async () => {
    mockConfirm.mockReturnValue(false);
    render(
      <Suspense fallback={<div>Loading...</div>}>
        <ModelDetailPage params={mockParams} />
      </Suspense>
    );

    await waitFor(() => {
      expect(screen.getByText('System Rule 1')).toBeInTheDocument();
    });

    const deleteButtons = screen.getAllByText('Delete');
    fireEvent.click(deleteButtons[0]);
    
    expect(mockConfirm).toHaveBeenCalled();
    expect(apiClient.delete).not.toHaveBeenCalled();
  });

  it('handles start, stop, and download model commands', async () => {
    (apiClient.post as jest.Mock).mockResolvedValue({ ...mockModel, status: 'running' });

    render(
      <Suspense fallback={<div>Loading...</div>}>
        <ModelDetailPage params={mockParams} />
      </Suspense>
    );

    await waitFor(() => {
      expect(screen.getByText('Start Model')).toBeInTheDocument();
    });

    // Start
    fireEvent.click(screen.getByText('Start Model'));
    expect(apiClient.post).toHaveBeenCalledWith('/models/model-1/start', {});

    // Mock response for stop button rendering
    (apiClient.get as jest.Mock).mockImplementation((url: string) => {
      if (url === '/models/model-1') return Promise.resolve({ ...mockModel, status: 'running' });
      if (url.startsWith('/proxies')) return Promise.resolve(mockRules);
      return Promise.resolve([]);
    });

    // Advance polling timer to trigger model details reload
    act(() => {
      jest.advanceTimersByTime(5000);
    });

    await waitFor(() => {
      expect(screen.getByText('Stop Model')).toBeInTheDocument();
    });

    // Stop
    (apiClient.post as jest.Mock).mockResolvedValue({ ...mockModel, status: 'stopped' });
    fireEvent.click(screen.getByText('Stop Model'));
    expect(apiClient.post).toHaveBeenCalledWith('/models/model-1/stop', {});

    // Wait for uvicorn model status to settle
    await waitFor(() => {
      expect(screen.getByText('Download GGUF')).not.toBeDisabled();
    });

    // Download
    (apiClient.post as jest.Mock).mockResolvedValue({ ...mockModel, status: 'downloading' });
    fireEvent.click(screen.getByText('Download GGUF'));
    expect(apiClient.post).toHaveBeenCalledWith('/models/model-1/download', {});
  });

  it('shows error modal if start model fails', async () => {
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    (apiClient.post as jest.Mock).mockRejectedValue(new Error('Failed to boot container'));

    render(
      <Suspense fallback={<div>Loading...</div>}>
        <ModelDetailPage params={mockParams} />
      </Suspense>
    );

    await waitFor(() => {
      expect(screen.getByText('Start Model')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Start Model'));

    await waitFor(() => {
      expect(screen.getByText(/Startup Failed/)).toBeInTheDocument();
      expect(screen.getByText('Failed to boot container')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Close'));
    await waitFor(() => {
      expect(screen.queryByText(/Startup Failed/)).not.toBeInTheDocument();
    });

    consoleSpy.mockRestore();
  });

  it('triggers test regex run after user inputs test text', async () => {
    (apiClient.post as jest.Mock).mockResolvedValue({ result: 'replaced text' });

    render(
      <Suspense fallback={<div>Loading...</div>}>
        <ModelDetailPage params={mockParams} />
      </Suspense>
    );

    await waitFor(() => {
      expect(screen.getByPlaceholderText('Enter text to test Match Patterns against...')).toBeInTheDocument();
    });

    const textarea = screen.getByPlaceholderText('Enter text to test Match Patterns against...');
    fireEvent.change(textarea, { target: { value: 'test raw text' } });

    // Fast forward testing timeout (400ms)
    act(() => {
      jest.advanceTimersByTime(500);
    });

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith('/proxies/test', {
        text: 'test raw text',
        model_id: 'model-1',
        chain: 'input_chain'
      });
      expect(screen.getByText('replaced text')).toBeInTheDocument();
    });
  });

  it('toggles rule active state', async () => {
    (apiClient.put as jest.Mock).mockResolvedValue({});

    render(
      <Suspense fallback={<div>Loading...</div>}>
        <ModelDetailPage params={mockParams} />
      </Suspense>
    );

    await waitFor(() => {
      expect(screen.getByText('System Rule 1')).toBeInTheDocument();
    });

    // Check click on status toggle
    const activeToggle = screen.getByRole('button', { name: 'Active' });
    fireEvent.click(activeToggle);

    expect(apiClient.put).toHaveBeenCalledWith('/proxies/rule-1', expect.objectContaining({
      id: 'rule-1',
      is_active: false
    }));
  });

  it('moves rules order up and down', async () => {
    (apiClient.put as jest.Mock).mockResolvedValue({});

    render(
      <Suspense fallback={<div>Loading...</div>}>
        <ModelDetailPage params={mockParams} />
      </Suspense>
    );

    await waitFor(() => {
      expect(screen.getByText('System Rule 2')).toBeInTheDocument();
    });

    // Move System Rule 2 up (upBtn at index 1 is enabled)
    const upBtn = screen.getAllByText('▲')[1];
    fireEvent.click(upBtn);

    // Swap ordering makes 3 PUT requests
    await waitFor(() => {
      expect(apiClient.put).toHaveBeenCalledTimes(3);
    });
  });

  it('opens Rule Modal for adding and submits it successfully', async () => {
    (apiClient.post as jest.Mock).mockResolvedValue({});

    render(
      <Suspense fallback={<div>Loading...</div>}>
        <ModelDetailPage params={mockParams} />
      </Suspense>
    );

    await waitFor(() => {
      expect(screen.getByText('Add Rule')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Add Rule'));

    // Verify modal is open. The modal title is 'Create Rule'
    const modalTitles = screen.getAllByText('Create Rule');
    // Ensure the h2 is in the document
    expect(modalTitles.some(el => el.tagName === 'H2')).toBe(true);

    fireEvent.change(screen.getByPlaceholderText('e.g. Clean trailing whitespace'), { target: { value: 'New Test Rule' } });
    fireEvent.change(screen.getByPlaceholderText(/hallucinate/), { target: { value: 'search-regex' } });
    fireEvent.change(screen.getByPlaceholderText('e.g. generate facts'), { target: { value: 'replace-regex' } });

    // Submit button also says 'Create Rule'
    const submitBtn = screen.getAllByRole('button', { name: 'Create Rule' }).find(el => el.getAttribute('type') === 'submit');
    fireEvent.click(submitBtn!);

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith('/proxies', {
        model_id: 'model-1',
        name: 'New Test Rule',
        pattern: 'search-regex',
        replacement: 'replace-regex',
        chain: 'input_chain',
        order: 3,
        is_active: true
      });
    });
  });

  it('opens Rule Modal for editing and submits it successfully', async () => {
    (apiClient.put as jest.Mock).mockResolvedValue({});

    render(
      <Suspense fallback={<div>Loading...</div>}>
        <ModelDetailPage params={mockParams} />
      </Suspense>
    );

    await waitFor(() => {
      expect(screen.getByText('System Rule 1')).toBeInTheDocument();
    });

    const editButtons = screen.getAllByText('Edit');
    fireEvent.click(editButtons[0]);

    expect(screen.getByText('Edit Rule')).toBeInTheDocument();
    expect(screen.getByDisplayValue('System Rule 1')).toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText('e.g. Clean trailing whitespace'), { target: { value: 'Modified Rule' } });
    fireEvent.click(screen.getByText('Save Changes'));

    await waitFor(() => {
      expect(apiClient.put).toHaveBeenCalledWith('/proxies/rule-1', expect.objectContaining({
        name: 'Modified Rule'
      }));
    });
  });

  it('shows alert message on modal submit error', async () => {
    (apiClient.post as jest.Mock).mockRejectedValue(new Error('Order must be unique'));

    render(
      <Suspense fallback={<div>Loading...</div>}>
        <ModelDetailPage params={mockParams} />
      </Suspense>
    );

    await waitFor(() => {
      expect(screen.getByText('Add Rule')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Add Rule'));
    fireEvent.change(screen.getByPlaceholderText('e.g. Clean trailing whitespace'), { target: { value: 'Conflicting Rule' } });
    fireEvent.change(screen.getByPlaceholderText(/hallucinate/), { target: { value: 'xyz' } });

    // Submit button inside modal says 'Create Rule'
    const submitBtn = screen.getAllByRole('button', { name: 'Create Rule' }).find(el => el.getAttribute('type') === 'submit');
    fireEvent.click(submitBtn!);

    await waitFor(() => {
      expect(mockAlert).toHaveBeenCalledWith('Order must be unique');
    });
  });
});
