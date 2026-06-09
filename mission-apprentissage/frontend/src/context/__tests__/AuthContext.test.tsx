import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AuthProvider, useAuth } from '../AuthContext';

vi.mock('@/api/auth', () => ({
  getMe: vi.fn(),
  login: vi.fn(),
  register: vi.fn(),
  logout: vi.fn(),
}));

import * as authApi from '@/api/auth';

const mockUser = { id: 1, username: 'testuser', email: 'test@example.com', role: 'user', created_at: '2024-01-01T00:00:00Z', updated_at: '2024-01-01T00:00:00Z' };
const adminUser = { id: 2, username: 'admin', email: 'admin@example.com', role: 'admin', created_at: '2024-01-01T00:00:00Z', updated_at: '2024-01-01T00:00:00Z' };

function TestConsumer() {
  const { user, isLoading, isAdmin, login, logout } = useAuth();
  if (isLoading) return <div>loading</div>;
  return (
    <div>
      <div data-testid="username">{user?.username ?? 'null'}</div>
      <div data-testid="isAdmin">{String(isAdmin)}</div>
      <button onClick={() => login('test@example.com', 'pass')}>login</button>
      <button onClick={() => logout()}>logout</button>
    </div>
  );
}

function renderWithAuth() {
  return render(<AuthProvider><TestConsumer /></AuthProvider>);
}

describe('AuthContext', () => {
  beforeEach(() => { vi.clearAllMocks(); });

  it('affiche loading puis null si getMe échoue', async () => {
    vi.mocked(authApi.getMe).mockRejectedValue(new Error('401'));
    renderWithAuth();
    expect(screen.getByText('loading')).toBeInTheDocument();
    await waitFor(() => expect(screen.getByTestId('username')).toHaveTextContent('null'));
    expect(screen.getByTestId('isAdmin')).toHaveTextContent('false');
  });

  it("charge l'utilisateur au montage si getMe réussit", async () => {
    vi.mocked(authApi.getMe).mockResolvedValue(mockUser);
    renderWithAuth();
    await waitFor(() => expect(screen.getByTestId('username')).toHaveTextContent('testuser'));
    expect(screen.getByTestId('isAdmin')).toHaveTextContent('false');
  });

  it('isAdmin est true quand le rôle est admin', async () => {
    vi.mocked(authApi.getMe).mockResolvedValue(adminUser);
    renderWithAuth();
    await waitFor(() => expect(screen.getByTestId('isAdmin')).toHaveTextContent('true'));
  });

  it('login appelle authApi.login puis getMe et met à jour user', async () => {
    vi.mocked(authApi.getMe)
      .mockRejectedValueOnce(new Error('401'))
      .mockResolvedValueOnce(mockUser);
    vi.mocked(authApi.login).mockResolvedValue(undefined);
    renderWithAuth();
    await waitFor(() => expect(screen.getByTestId('username')).toHaveTextContent('null'));
    await act(async () => {
      await userEvent.click(screen.getByRole('button', { name: 'login' }));
    });
    expect(authApi.login).toHaveBeenCalledWith({ email: 'test@example.com', password: 'pass' });
    await waitFor(() => expect(screen.getByTestId('username')).toHaveTextContent('testuser'));
  });

  it('logout appelle authApi.logout et remet user à null', async () => {
    vi.mocked(authApi.getMe).mockResolvedValue(mockUser);
    vi.mocked(authApi.logout).mockResolvedValue(undefined);
    renderWithAuth();
    await waitFor(() => expect(screen.getByTestId('username')).toHaveTextContent('testuser'));
    await act(async () => {
      await userEvent.click(screen.getByRole('button', { name: 'logout' }));
    });
    expect(authApi.logout).toHaveBeenCalled();
    await waitFor(() => expect(screen.getByTestId('username')).toHaveTextContent('null'));
  });

  it('useAuth lève une erreur si utilisé hors AuthProvider', () => {
    function BadConsumer() { useAuth(); return null; }
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    expect(() => render(<BadConsumer />)).toThrow('useAuth must be used within an AuthProvider');
    consoleSpy.mockRestore();
  });
});
