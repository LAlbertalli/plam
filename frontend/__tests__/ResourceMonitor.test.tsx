import { render, screen, act } from '@testing-library/react';
import ResourceMonitor from '@/components/ResourceMonitor';

describe('ResourceMonitor', () => {
  let mockWebSocket: any;

  beforeEach(() => {
    mockWebSocket = {
      onmessage: null,
      close: jest.fn(),
    };
    (global as any).WebSocket = jest.fn(() => mockWebSocket);
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  it('renders nothing initially', () => {
    const { container } = render(<ResourceMonitor />);
    expect(container).toBeEmptyDOMElement();
  });

  it('renders metrics when data is received', () => {
    render(<ResourceMonitor />);

    // Simulate receiving a message
    act(() => {
      mockWebSocket.onmessage({
        data: JSON.stringify({
          cpu_percent: 45.2,
          ram_total_mb: 32768,
          ram_used_mb: 16384,
          ram_free_mb: 16384
        })
      });
    });

    expect(screen.getByText('System Resources')).toBeInTheDocument();
    expect(screen.getByText('45.2%')).toBeInTheDocument();
    expect(screen.getByText('16.0 / 32.0 GB')).toBeInTheDocument();
  });
});
