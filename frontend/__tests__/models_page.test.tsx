import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import ModelsPage from '@/app/models/page';
import { apiClient } from '@/lib/api';

// Mock the API client
jest.mock('@/lib/api', () => ({
  apiClient: {
    get: jest.fn(),
    post: jest.fn(),
    delete: jest.fn(),
  }
}));

describe('ModelsPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders loading state initially', () => {
    (apiClient.get as jest.Mock).mockReturnValue(new Promise(() => {}));
    render(<ModelsPage />);
    expect(screen.getByText('Loading models...')).toBeInTheDocument();
  });

  it('fetches and displays models', async () => {
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
      }
    ];

    (apiClient.get as jest.Mock).mockResolvedValue(mockModels);

    render(<ModelsPage />);

    await waitFor(() => {
      expect(screen.getByText('Llama-3-8B')).toBeInTheDocument();
    });
    
    expect(screen.getByText('stopped')).toBeInTheDocument();
    expect(screen.getByText('8.0 GB')).toBeInTheDocument();
  });

  it('triggers download when download button is clicked', async () => {
    const mockModels = [
      {
        id: '1',
        name: 'Llama-3-8B',
        status: 'stopped',
        ram_required_mb: 8192,
        context_size: 4096,
        llamacpp_version_hash: 'ff52ee9'
      }
    ];

    (apiClient.get as jest.Mock).mockResolvedValue(mockModels);
    (apiClient.post as jest.Mock).mockResolvedValue({});

    render(<ModelsPage />);

    await waitFor(() => {
      expect(screen.getByText('Actions ▾')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Actions ▾'));

    await waitFor(() => {
      expect(screen.getByText('Download')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Download'));

    expect(apiClient.post).toHaveBeenCalledWith('/models/1/download', {});
  });
});
