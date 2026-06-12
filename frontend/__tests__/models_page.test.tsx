import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import ModelsPage from '@/app/models/page';
import { apiClient } from '@/lib/api';

// Mock the API client
jest.mock('@/lib/api', () => ({
  apiClient: {
    get: jest.fn(),
    post: jest.fn(),
    put: jest.fn(),
    delete: jest.fn(),
  }
}));

// Mock ModelModal component to isolate ModelsPage tests
jest.mock('@/components/ModelModal', () => {
  return function MockModelModal({ onSuccess, onClose }: any) {
    return (
      <div data-testid="mock-modal">
        <button onClick={onSuccess}>Success</button>
        <button onClick={onClose}>Close</button>
      </div>
    );
  };
});

// Mock window.confirm
const mockConfirm = jest.fn();
Object.defineProperty(window, 'confirm', {
  value: mockConfirm
});

describe('ModelsPage', () => {
  const mockModels = [
    {
      id: '1',
      name: 'Llama-3-8B',
      hf_repo_id: 'meta-llama/Llama-3-8B',
      gguf_filename: 'model.gguf',
      status: 'stopped',
      ram_required_mb: 8192,
      context_size: 4096,
      llamacpp_version_hash: 'ff52ee9'
    },
    {
      id: '2',
      name: 'Mistral-7B',
      hf_repo_id: 'mistralai/Mistral-7B',
      gguf_filename: 'mistral.gguf',
      status: 'running',
      ram_required_mb: 4096,
      context_size: 2048,
      llamacpp_version_hash: 'ff52ee9'
    }
  ];

  beforeEach(() => {
    jest.clearAllMocks();
    (apiClient.get as jest.Mock).mockResolvedValue(mockModels);
  });

  it('renders loading state initially', () => {
    (apiClient.get as jest.Mock).mockReturnValue(new Promise(() => {}));
    render(<ModelsPage />);
    expect(screen.getByText('Loading models...')).toBeInTheDocument();
  });

  it('fetches and displays models', async () => {
    render(<ModelsPage />);

    await waitFor(() => {
      expect(screen.getByText('Llama-3-8B')).toBeInTheDocument();
      expect(screen.getByText('Mistral-7B')).toBeInTheDocument();
    });
    
    expect(screen.getByText('stopped')).toBeInTheDocument();
    expect(screen.getByText('running')).toBeInTheDocument();
    expect(screen.getByText('8.0 GB')).toBeInTheDocument();
    expect(screen.getByText('4.0 GB')).toBeInTheDocument();
  });

  it('triggers start when start button is clicked', async () => {
    (apiClient.post as jest.Mock).mockResolvedValue({});
    render(<ModelsPage />);

    await waitFor(() => {
      expect(screen.getAllByText('Actions ▾')).toHaveLength(2);
    });

    // Open first dropdown (Llama-3-8B is stopped)
    fireEvent.click(screen.getAllByText('Actions ▾')[0]);

    await waitFor(() => {
      expect(screen.getByText('Start')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Start'));
    expect(apiClient.post).toHaveBeenCalledWith('/models/1/start', {});
  });

  it('triggers stop when stop button is clicked', async () => {
    (apiClient.post as jest.Mock).mockResolvedValue({});
    render(<ModelsPage />);

    await waitFor(() => {
      expect(screen.getAllByText('Actions ▾')).toHaveLength(2);
    });

    // Open second dropdown (Mistral-7B is running)
    fireEvent.click(screen.getAllByText('Actions ▾')[1]);

    await waitFor(() => {
      expect(screen.getByText('Stop')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Stop'));
    expect(apiClient.post).toHaveBeenCalledWith('/models/2/stop', {});
  });

  it('triggers download when download button is clicked', async () => {
    (apiClient.post as jest.Mock).mockResolvedValue({});
    render(<ModelsPage />);

    await waitFor(() => {
      expect(screen.getAllByText('Actions ▾')).toHaveLength(2);
    });

    fireEvent.click(screen.getAllByText('Actions ▾')[0]);

    await waitFor(() => {
      expect(screen.getByText('Download')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Download'));
    expect(apiClient.post).toHaveBeenCalledWith('/models/1/download', {});
  });

  it('triggers delete when delete button is clicked and confirmed', async () => {
    mockConfirm.mockReturnValue(true);
    (apiClient.delete as jest.Mock).mockResolvedValue({});
    render(<ModelsPage />);

    await waitFor(() => {
      expect(screen.getAllByText('Actions ▾')).toHaveLength(2);
    });

    fireEvent.click(screen.getAllByText('Actions ▾')[0]);

    await waitFor(() => {
      expect(screen.getByText('Delete')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Delete'));
    expect(mockConfirm).toHaveBeenCalled();
    expect(apiClient.delete).toHaveBeenCalledWith('/models/1');
  });

  it('triggers delete but does nothing if not confirmed', async () => {
    mockConfirm.mockReturnValue(false);
    render(<ModelsPage />);

    await waitFor(() => {
      expect(screen.getAllByText('Actions ▾')).toHaveLength(2);
    });

    fireEvent.click(screen.getAllByText('Actions ▾')[0]);

    await waitFor(() => {
      expect(screen.getByText('Delete')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Delete'));
    expect(mockConfirm).toHaveBeenCalled();
    expect(apiClient.delete).not.toHaveBeenCalled();
  });

  it('shows error modal when model fails to start', async () => {
    (apiClient.post as jest.Mock).mockRejectedValue(new Error('GPU Out of Memory'));
    render(<ModelsPage />);

    await waitFor(() => {
      expect(screen.getAllByText('Actions ▾')).toHaveLength(2);
    });

    fireEvent.click(screen.getAllByText('Actions ▾')[0]);

    await waitFor(() => {
      expect(screen.getByText('Start')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Start'));

    await waitFor(() => {
      expect(screen.getByText('⚠️ Startup Failed: Llama-3-8B')).toBeInTheDocument();
      expect(screen.getByText('GPU Out of Memory')).toBeInTheDocument();
    });

    // Close error modal
    fireEvent.click(screen.getByText('Close'));
    await waitFor(() => {
      expect(screen.queryByText('⚠️ Startup Failed: Llama-3-8B')).not.toBeInTheDocument();
    });
  });

  it('handles start rejection with non-Error object', async () => {
    (apiClient.post as jest.Mock).mockRejectedValue('String error');
    render(<ModelsPage />);

    await waitFor(() => {
      expect(screen.getAllByText('Actions ▾')).toHaveLength(2);
    });

    fireEvent.click(screen.getAllByText('Actions ▾')[0]);

    await waitFor(() => {
      expect(screen.getByText('Start')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Start'));

    await waitFor(() => {
      expect(screen.getByText('⚠️ Startup Failed: Llama-3-8B')).toBeInTheDocument();
      expect(screen.getByText('An unknown error occurred during startup.')).toBeInTheDocument();
    });
  });

  it('logs error when stop fails', async () => {
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    (apiClient.post as jest.Mock).mockRejectedValue(new Error('Stop failed'));
    render(<ModelsPage />);

    await waitFor(() => {
      expect(screen.getAllByText('Actions ▾')).toHaveLength(2);
    });

    fireEvent.click(screen.getAllByText('Actions ▾')[1]);

    await waitFor(() => {
      expect(screen.getByText('Stop')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Stop'));
    await waitFor(() => {
      expect(consoleSpy).toHaveBeenCalledWith('Failed to stop model:', expect.any(Error));
    });
    consoleSpy.mockRestore();
  });

  it('logs error when download fails', async () => {
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    (apiClient.post as jest.Mock).mockRejectedValue(new Error('Download failed'));
    render(<ModelsPage />);

    await waitFor(() => {
      expect(screen.getAllByText('Actions ▾')).toHaveLength(2);
    });

    fireEvent.click(screen.getAllByText('Actions ▾')[0]);

    await waitFor(() => {
      expect(screen.getByText('Download')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Download'));
    await waitFor(() => {
      expect(consoleSpy).toHaveBeenCalledWith('Failed to start download:', expect.any(Error));
    });
    consoleSpy.mockRestore();
  });

  it('logs error when delete fails', async () => {
    mockConfirm.mockReturnValue(true);
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    (apiClient.delete as jest.Mock).mockRejectedValue(new Error('Delete failed'));
    render(<ModelsPage />);

    await waitFor(() => {
      expect(screen.getAllByText('Actions ▾')).toHaveLength(2);
    });

    fireEvent.click(screen.getAllByText('Actions ▾')[0]);

    await waitFor(() => {
      expect(screen.getByText('Delete')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Delete'));
    await waitFor(() => {
      expect(consoleSpy).toHaveBeenCalledWith('Failed to delete model:', expect.any(Error));
    });
    consoleSpy.mockRestore();
  });

  it('opens Modal when clicking Add a model', async () => {
    render(<ModelsPage />);
    
    await waitFor(() => expect(screen.getByText('Llama-3-8B')).toBeInTheDocument());

    fireEvent.click(screen.getByText('Add a model'));
    expect(screen.getByTestId('mock-modal')).toBeInTheDocument();
  });

  it('opens Modal when clicking Edit on an action item', async () => {
    render(<ModelsPage />);
    
    await waitFor(() => expect(screen.getByText('Llama-3-8B')).toBeInTheDocument());

    fireEvent.click(screen.getAllByText('Actions ▾')[0]);
    await waitFor(() => expect(screen.getByText('Edit')).toBeInTheDocument());

    fireEvent.click(screen.getByText('Edit'));
    expect(screen.getByTestId('mock-modal')).toBeInTheDocument();
  });
});
