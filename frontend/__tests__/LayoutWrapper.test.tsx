import { render, screen, fireEvent, act } from '@testing-library/react';
import LayoutWrapper from '@/components/LayoutWrapper';

// Mock the Sidebar component
jest.mock('@/components/Sidebar', () => {
  return function MockSidebar({ isCollapsed, toggleSidebar }: any) {
    return (
      <div data-testid="mock-sidebar">
        <span>Collapsed: {String(isCollapsed)}</span>
        <button onClick={toggleSidebar}>Toggle</button>
      </div>
    );
  };
});

describe('LayoutWrapper', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
    Object.defineProperty(window, 'innerWidth', { writable: true, configurable: true, value: 1024 });
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('renders correctly on desktop expanded by default', () => {
    render(
      <LayoutWrapper>
        <div>Content</div>
      </LayoutWrapper>
    );

    act(() => {
      jest.advanceTimersByTime(10);
    });

    expect(screen.getByTestId('mock-sidebar')).toHaveTextContent('Collapsed: false');
    expect(screen.getByText('Content')).toBeInTheDocument();
  });

  it('restores desktop collapsed state from localStorage', () => {
    localStorage.setItem('sidebar-desktop-collapsed', 'true');
    render(
      <LayoutWrapper>
        <div>Content</div>
      </LayoutWrapper>
    );

    act(() => {
      jest.advanceTimersByTime(10);
    });

    expect(screen.getByTestId('mock-sidebar')).toHaveTextContent('Collapsed: true');
    expect(screen.getByRole('button', { name: 'Toggle Navigation Sidebar' })).toBeInTheDocument();
  });

  it('toggles desktop collapsed state on button click and saves to localStorage', () => {
    render(
      <LayoutWrapper>
        <div>Content</div>
      </LayoutWrapper>
    );

    act(() => {
      jest.advanceTimersByTime(10);
    });

    expect(screen.getByTestId('mock-sidebar')).toHaveTextContent('Collapsed: false');

    const toggleBtn = screen.getByRole('button', { name: 'Toggle' });
    fireEvent.click(toggleBtn);

    expect(screen.getByTestId('mock-sidebar')).toHaveTextContent('Collapsed: true');
    expect(localStorage.getItem('sidebar-desktop-collapsed')).toBe('true');

    fireEvent.click(toggleBtn);
    expect(screen.getByTestId('mock-sidebar')).toHaveTextContent('Collapsed: false');
    expect(localStorage.getItem('sidebar-desktop-collapsed')).toBe('false');
  });

  it('toggles mobile layout on resize and handles menu open/close', () => {
    Object.defineProperty(window, 'innerWidth', { writable: true, configurable: true, value: 500 });
    
    const { container } = render(
      <LayoutWrapper>
        <div>Content</div>
      </LayoutWrapper>
    );

    act(() => {
      jest.advanceTimersByTime(10);
    });

    // Mobile initial state: activeCollapsed = true (closed menu)
    expect(screen.getByTestId('mock-sidebar')).toHaveTextContent('Collapsed: true');
    
    const toggleBtn = screen.getByRole('button', { name: 'Toggle' });
    
    // Toggle: opens menu on mobile (activeCollapsed = false)
    fireEvent.click(toggleBtn);
    expect(screen.getByTestId('mock-sidebar')).toHaveTextContent('Collapsed: false');

    // Clicking the backdrop should close it
    const backdrop = container.querySelector('[class*="backdrop"]');
    expect(backdrop).toBeInTheDocument();
    
    fireEvent.click(backdrop!);
    expect(screen.getByTestId('mock-sidebar')).toHaveTextContent('Collapsed: true');
  });

  it('reacts to window resize events', () => {
    render(
      <LayoutWrapper>
        <div>Content</div>
      </LayoutWrapper>
    );

    act(() => {
      jest.advanceTimersByTime(10);
    });

    expect(screen.getByTestId('mock-sidebar')).toHaveTextContent('Collapsed: false');

    // Resize to mobile
    act(() => {
      Object.defineProperty(window, 'innerWidth', { value: 500 });
      window.dispatchEvent(new Event('resize'));
    });

    expect(screen.getByTestId('mock-sidebar')).toHaveTextContent('Collapsed: true');
  });
});
