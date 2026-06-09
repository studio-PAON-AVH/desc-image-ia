import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { Login } from '../Login';

vi.mock('@/context/AuthContext', () => ({
  useAuth: vi.fn(),
}));

vi.mock('axios', async (importOriginal) => {
  const actual = await importOriginal<typeof import('axios')>();
  return {
    ...actual,
    default: {
      ...actual.default,
      isAxiosError: (err: unknown) => (err as { isAxiosError?: boolean }).isAxiosError === true,
    },
    isAxiosError: (err: unknown) => (err as { isAxiosError?: boolean }).isAxiosError === true,
  };
});

import { useAuth } from '@/context/AuthContext';

function renderLogin() {
  return render(
    <MemoryRouter initialEntries={['/login']}>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/dashboard" element={<div>dashboard</div>} />
      </Routes>
    </MemoryRouter>
  );
}

const baseAuth = {
  user: null,
  isLoading: false,
  isAdmin: false,
  login: vi.fn(),
  register: vi.fn(),
  logout: vi.fn(),
};

describe('Page Login', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('affiche le formulaire de connexion', () => {
    vi.mocked(useAuth).mockReturnValue({ ...baseAuth });
    renderLogin();

    // Label "Adresse e-mail" est lié à l'input via htmlFor="email"
    expect(screen.getByLabelText(/adresse e-mail/i)).toBeInTheDocument();
    // Label "Mot de passe" est lié à l'input via htmlFor="password"
    expect(screen.getByLabelText(/mot de passe/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /se connecter/i })).toBeInTheDocument();
  });

  it('appelle login avec les bonnes valeurs', async () => {
    const mockLogin = vi.fn().mockResolvedValue(undefined);
    vi.mocked(useAuth).mockReturnValue({ ...baseAuth, login: mockLogin });
    renderLogin();

    const emailField = screen.getByLabelText(/adresse e-mail/i);
    const passwordField = screen.getByLabelText(/mot de passe/i);

    await userEvent.type(emailField, 'user@test.com');
    await userEvent.type(passwordField, 'monmotdepasse');
    await userEvent.click(screen.getByRole('button', { name: /se connecter/i }));

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith('user@test.com', 'monmotdepasse');
    });
  });

  it('affiche une erreur si login échoue (erreur générique)', async () => {
    const mockLogin = vi.fn().mockRejectedValue(new Error('Network error'));
    vi.mocked(useAuth).mockReturnValue({ ...baseAuth, login: mockLogin });
    renderLogin();

    await userEvent.type(screen.getByLabelText(/adresse e-mail/i), 'bad@test.com');
    await userEvent.type(screen.getByLabelText(/mot de passe/i), 'wrongpass');
    await userEvent.click(screen.getByRole('button', { name: /se connecter/i }));

    await waitFor(() => {
      // Login.tsx affiche l'erreur dans un <Alert variant="destructive"> → <AlertDescription>
      expect(screen.getByText(/impossible de se connecter/i)).toBeInTheDocument();
    });
  });

  it('affiche une erreur 401 si identifiants incorrects', async () => {
    const axiosError = Object.assign(new Error('Unauthorized'), {
      isAxiosError: true,
      response: { status: 401 },
    });
    const mockLogin = vi.fn().mockRejectedValue(axiosError);
    vi.mocked(useAuth).mockReturnValue({ ...baseAuth, login: mockLogin });
    renderLogin();

    await userEvent.type(screen.getByLabelText(/adresse e-mail/i), 'bad@test.com');
    await userEvent.type(screen.getByLabelText(/mot de passe/i), 'wrongpass');
    await userEvent.click(screen.getByRole('button', { name: /se connecter/i }));

    await waitFor(() => {
      expect(screen.getByText(/adresse e-mail ou mot de passe incorrect/i)).toBeInTheDocument();
    });
  });

  it('redirige vers /dashboard si user est déjà connecté', () => {
    vi.mocked(useAuth).mockReturnValue({
      ...baseAuth,
      user: { id: 1, username: 'Alice', email: 'alice@test.com', role: 'user', created_at: '2024-01-01T00:00:00Z', updated_at: '2024-01-01T00:00:00Z' },
    });
    renderLogin();
    expect(screen.getByText('dashboard')).toBeInTheDocument();
  });

  it('ne rend rien si authLoading est true', () => {
    vi.mocked(useAuth).mockReturnValue({ ...baseAuth, isLoading: true });
    const { container } = renderLogin();
    expect(container.firstChild).toBeNull();
  });
});
