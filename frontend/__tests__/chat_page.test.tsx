import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import ChatPage from '@/app/chat/page';
import { apiClient } from '@/lib/api';
import { TextEncoder, TextDecoder } from 'util';

global.TextEncoder = TextEncoder as any;
global.TextDecoder = TextDecoder as any;

jest.mock('next/navigation', () => ({
  usePathname: () => '/chat',
  useRouter: () => ({
    push: jest.fn(),
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

// Mock global.fetch
const mockReader = {
  read: jest.fn()
};
const mockResponse = {
  ok: true,
  body: {
    getReader: () => mockReader
  }
};
const globalFetch = jest.fn(() => Promise.resolve(mockResponse));
global.fetch = globalFetch as any;

describe('ChatPage', () => {
  const mockAgents = [{ id: 'agent-1', name: 'Python Expert' }];
  const mockSessions = [{ id: 'session-1', title: 'Discussion 1', created_at: '2026-05-22' }];
  const mockHistory = [
    {
      id: 'msg-1',
      session_id: 'session-1',
      sequence_id: 1,
      role: 'user',
      content: 'Hello agent',
      timestamp: '2026-05-22'
    },
    {
      id: 'msg-2',
      session_id: 'session-1',
      sequence_id: 2,
      role: 'assistant',
      content: 'Hi user',
      thinking_trace: 'Inside thought trace',
      timestamp: '2026-05-22'
    }
  ];

  beforeEach(() => {
    jest.clearAllMocks();
    (apiClient.get as jest.Mock).mockImplementation((url: string) => {
      if (url === '/agents') return Promise.resolve(mockAgents);
      if (url === '/chat/sessions') return Promise.resolve(mockSessions);
      if (url === '/chat/sessions/session-1/history') return Promise.resolve(mockHistory);
      return Promise.resolve([]);
    });
  });

  it('renders loading state initially', () => {
    (apiClient.get as jest.Mock).mockReturnValue(new Promise(() => {}));
    render(<ChatPage />);
    expect(screen.getByText('Loading chat interface...')).toBeInTheDocument();
  });

  it('renders and displays active chat content', async () => {
    render(<ChatPage />);

    await waitFor(() => {
      expect(screen.getByText('Talking to')).toBeInTheDocument();
      expect(screen.getByText('Python Expert')).toBeInTheDocument();
      expect(screen.getByText('Hello agent')).toBeInTheDocument();
      expect(screen.getByText('Hi user')).toBeInTheDocument();
    });
  });

  it('toggles thinking trace folded drawer', async () => {
    render(<ChatPage />);
    
    await waitFor(() => expect(screen.getByText('Hi user')).toBeInTheDocument());

    const toggleBtn = screen.getByText('🧠 Show thinking ▾');
    fireEvent.click(toggleBtn);


    expect(screen.getByText('Inside thought trace')).toBeInTheDocument();
  });

  it('submits a user message and handles stream reader reading chunks', async () => {
    // Setup mock reader to return two chunks: a text chunk, then a done chunk
    const encoder = new TextEncoder();
    mockReader.read
      .mockResolvedValueOnce({
        done: false,
        value: encoder.encode('data: {"index": 0, "text": "I am thinking"}\n\n')
      })
      .mockResolvedValueOnce({
        done: false,
        value: encoder.encode('data: {"done": true}\n\n')
      })
      .mockResolvedValueOnce({
        done: true,
        value: undefined
      });

    render(<ChatPage />);
    
    await waitFor(() => expect(screen.getByText('Hello agent')).toBeInTheDocument());

    const input = screen.getByPlaceholderText('Type a message, press Enter to send...');
    fireEvent.change(input, { target: { value: 'How is the weather?' } });

    const sendBtn = screen.getByText('⚡ Send');
    fireEvent.click(sendBtn);

    await waitFor(() => {
      expect(globalFetch).toHaveBeenCalled();
      // It should pull updated history and refresh
      expect(apiClient.get).toHaveBeenCalledWith('/chat/sessions/session-1/history');
    });
  });
});
