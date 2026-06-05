import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import Sidebar from '@/components/Sidebar';
import { apiClient } from '@/lib/api';

// Mock next/navigation
const mockPush = jest.fn();
jest.mock('next/navigation', () => ({
  usePathname: () => '/chat',
  useRouter: () => ({
    push: mockPush,
    replace: jest.fn()
  }),
  useSearchParams: () => ({
    get: (key: string) => 'session-1'
  })
}));

jest.mock('@/lib/api', () => ({
  apiClient: {
    get: jest.fn(),
    post: jest.fn(),
    delete: jest.fn()
  }
}));

// Mock window.confirm
const mockConfirm = jest.fn();
Object.defineProperty(window, 'confirm', {
  value: mockConfirm
});

describe('Sidebar', () => {
  const mockSessions = [{ id: 'session-1', title: 'Discussion 1' }];

  beforeEach(() => {
    jest.clearAllMocks();
    (apiClient.get as jest.Mock).mockImplementation((url: string) => {
      if (url === '/chat/sessions') return Promise.resolve(mockSessions);
      return Promise.resolve([]);
    });
  });

  it('renders logo and navigation links', async () => {
    render(<Sidebar />);
    expect(screen.getByText('PLAM')).toBeInTheDocument();
    expect(screen.getByText('Models')).toBeInTheDocument();
    expect(screen.getByText('Agents')).toBeInTheDocument();
    expect(screen.getByText('Chat')).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText('💬 Discussion 1')).toBeInTheDocument();
    });
  });

  it('creates new session when clicking New Chat', async () => {
    (apiClient.post as jest.Mock).mockResolvedValue({ id: 'session-2', title: 'New Discussion' });
    render(<Sidebar />);
    
    await waitFor(() => expect(screen.getByText('💬 Discussion 1')).toBeInTheDocument());

    fireEvent.click(screen.getByText('➕ New Chat'));

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith('/chat/sessions', { title: 'New Discussion' });
      expect(mockPush).toHaveBeenCalledWith('/chat?session_id=session-2');
    });
  });

  it('deletes session when clicking delete button and confirming', async () => {
    mockConfirm.mockReturnValue(true);
    (apiClient.delete as jest.Mock).mockResolvedValue({});
    render(<Sidebar />);
    
    await waitFor(() => expect(screen.getByText('💬 Discussion 1')).toBeInTheDocument());

    // Click '✕' button next to Discussion 1
    fireEvent.click(screen.getByText('✕'));

    expect(mockConfirm).toHaveBeenCalled();
    await waitFor(() => {
      expect(apiClient.delete).toHaveBeenCalledWith('/chat/sessions/session-1');
    });
  });
});
