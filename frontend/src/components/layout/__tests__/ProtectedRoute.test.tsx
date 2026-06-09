import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { ProtectedRoute } from '../ProtectedRoute';

vi.mock('@/context/AuthContext', () => ({
  useAuth: vi.fn(),
}));

vi.mock('../Navbar', () => ({
  Navbar: () => <nav>navbar</nav>,
}));

import { useAuth } from '@/context/AuthContext';

function mockAuth(user: object | null, isLoading = false) {
  vi.mocked(useAuth).mockReturnValue({
    user: user as any,
    isLoading,
    isAdmin: false,
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
  });
}

function renderProtected() {
  return render(
    <MemoryRouter initialEntries={['/dashboard']}>
      <Routes>
        <Route element={<ProtectedRoute />}>
          <Route path="/dashboard" element={<div>page protégée</div>} />
        </Route>
        <Route path="/login" element={<div>page login</div>} />
      </Routes>
    </MemoryRouter>
  );
}

describe('ProtectedRoute', () => {
  it("affiche le contenu si l'utilisateur est connecté", () => {
    mockAuth({ id: 1, role: 'user' });
    renderProtected();
    expect(screen.getByText('page protégée')).toBeInTheDocument();
  });

  it('redirige vers login si utilisateur null', () => {
    mockAuth(null);
    renderProtected();
    expect(screen.getByText('page login')).toBeInTheDocument();
    expect(screen.queryByText('page protégée')).not.toBeInTheDocument();
  });

  it('affiche un spinner pendant le chargement', () => {
    mockAuth(null, true);
    renderProtected();
    expect(screen.getByRole('status')).toBeInTheDocument();
    expect(screen.queryByText('page login')).not.toBeInTheDocument();
    expect(screen.queryByText('page protégée')).not.toBeInTheDocument();
  });
});
