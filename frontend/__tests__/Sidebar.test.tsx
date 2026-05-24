import { render, screen } from '@testing-library/react';
import Sidebar from '@/components/Sidebar';

// Mock next/navigation and api client
jest.mock('next/navigation', () => ({
  usePathname: () => '/models',
  useRouter: () => ({
    push: jest.fn(),
    replace: jest.fn()
  }),
  useSearchParams: () => ({
    get: () => null
  })
}));

jest.mock('@/lib/api', () => ({
  apiClient: {
    get: jest.fn(() => Promise.resolve([])),
    post: jest.fn(() => Promise.resolve({ id: 'new-session-id' }))
  }
}));


describe('Sidebar', () => {
  it('renders logo and navigation links', () => {
    render(<Sidebar />);
    expect(screen.getByText('PLAM')).toBeInTheDocument();
    expect(screen.getByText('Models')).toBeInTheDocument();
    expect(screen.getByText('Agents')).toBeInTheDocument();
    expect(screen.queryByText('Regex Rules')).not.toBeInTheDocument();
    expect(screen.getByText('Chat')).toBeInTheDocument();
  });


  it('marks active link based on pathname', () => {
    const { container } = render(<Sidebar />);
    const activeLink = container.querySelector('.active');
    expect(activeLink).toBeInTheDocument();
    expect(activeLink?.textContent).toContain('Models');
  });
});
