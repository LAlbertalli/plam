import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import AgentsPage from '@/app/agents/page';
import { apiClient } from '@/lib/api';

jest.mock('@/lib/api', () => ({
  apiClient: {
    get: jest.fn(),
    post: jest.fn(),
    put: jest.fn(),
    delete: jest.fn()
  }
}));

// Mock window.confirm
const mockConfirm = jest.fn();
Object.defineProperty(window, 'confirm', {
  value: mockConfirm
});

describe('AgentsPage', () => {
  const mockAgents = [
    {
      id: 'agent-1',
      name: 'Python Expert',
      description: 'Writes clean code',
      model_id: 'model-1',
      system_prompt: 'You are a python expert.',
      is_orchestrator: true,
      is_abstract: false
    }
  ];
  
  const mockModels = [
    {
      id: 'model-1',
      name: 'Llama-3-8B'
    }
  ];

  beforeEach(() => {
    jest.clearAllMocks();
    (apiClient.get as jest.Mock).mockImplementation((url: string) => {
      if (url === '/agents') return Promise.resolve(mockAgents);
      if (url === '/models') return Promise.resolve(mockModels);
      return Promise.resolve([]);
    });
  });

  it('renders loading state initially', () => {
    (apiClient.get as jest.Mock).mockReturnValue(new Promise(() => {}));
    render(<AgentsPage />);
    expect(screen.getByText('Loading agents...')).toBeInTheDocument();
  });

  it('renders and displays agents and matching models', async () => {
    render(<AgentsPage />);

    await waitFor(() => {
      expect(screen.getByText('Python Expert')).toBeInTheDocument();
      expect(screen.getByText('Writes clean code')).toBeInTheDocument();
      expect(screen.getByText('🤖 Llama-3-8B')).toBeInTheDocument();
      expect(screen.getByText('Orchestrator')).toBeInTheDocument();
    });
  });

  it('opens create modal when clicking Create Agent', async () => {
    render(<AgentsPage />);
    
    await waitFor(() => expect(screen.getByText('Python Expert')).toBeInTheDocument());

    const createBtn = screen.getByText('Create Agent');
    fireEvent.click(createBtn);

    expect(screen.getByText('Cancel')).toBeInTheDocument();
  });

  it('submits create form and sends POST request', async () => {
    (apiClient.post as jest.Mock).mockResolvedValue({ id: 'new-agent' });
    
    render(<AgentsPage />);
    
    await waitFor(() => expect(screen.getByText('Python Expert')).toBeInTheDocument());

    const createBtn = screen.getByText('Create Agent');
    fireEvent.click(createBtn);

    fireEvent.change(screen.getByPlaceholderText('e.g. Coder Agent'), { target: { value: 'New Agent' } });
    fireEvent.change(screen.getByPlaceholderText('e.g. Specialized in Python code compilation'), { target: { value: 'New desc' } });
    fireEvent.change(screen.getByPlaceholderText('Describe how the agent behaves, instructions it must follow, and its format requirements...'), { target: { value: 'Prompt' } });
    
    const submitBtn = screen.getByText('Create Agent', { selector: 'button.submitBtn' });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith('/agents', {
        name: 'New Agent',
        description: 'New desc',
        model_id: 'model-1',
        system_prompt: 'Prompt',
        is_orchestrator: false,
        is_abstract: false
      });
    });
  });

  it('opens edit modal and sends PUT request on edit submit', async () => {
    (apiClient.put as jest.Mock).mockResolvedValue({ id: 'agent-1' });
    
    render(<AgentsPage />);
    
    await waitFor(() => expect(screen.getByText('Python Expert')).toBeInTheDocument());

    const editBtn = screen.getByText('Edit');
    fireEvent.click(editBtn);

    fireEvent.change(screen.getByPlaceholderText('e.g. Coder Agent'), { target: { value: 'Updated Agent' } });
    
    const saveBtn = screen.getByRole('button', { name: 'Save Changes' });
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(apiClient.put).toHaveBeenCalledWith('/agents/agent-1', expect.objectContaining({
        name: 'Updated Agent'
      }));
    });
  });

  it('triggers delete agent when delete is clicked and confirmed', async () => {
    mockConfirm.mockReturnValue(true);
    (apiClient.delete as jest.Mock).mockResolvedValue({ status: 'ok' });

    render(<AgentsPage />);
    
    await waitFor(() => expect(screen.getByText('Python Expert')).toBeInTheDocument());

    const deleteBtn = screen.getByText('Delete');
    fireEvent.click(deleteBtn);

    expect(mockConfirm).toHaveBeenCalled();
    await waitFor(() => {
      expect(apiClient.delete).toHaveBeenCalledWith('/agents/agent-1');
    });
  });

  it('does not delete agent when confirm is rejected', async () => {
    mockConfirm.mockReturnValue(false);

    render(<AgentsPage />);
    
    await waitFor(() => expect(screen.getByText('Python Expert')).toBeInTheDocument());

    const deleteBtn = screen.getByText('Delete');
    fireEvent.click(deleteBtn);

    expect(mockConfirm).toHaveBeenCalled();
    expect(apiClient.delete).not.toHaveBeenCalled();
  });
});
