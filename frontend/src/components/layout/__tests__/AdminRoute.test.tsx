import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { AdminRoute } from '../AdminRoute';

vi.mock('@/context/AuthContext', () => ({
  useAuth: vi.fn(),
}));

import { useAuth } from '@/context/AuthContext';

function mockAuth(user: object | null, isAdmin: boolean, isLoading = false) {
  vi.mocked(useAuth).mockReturnValue({
    user: user as any,
    isLoading,
    isAdmin,
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
  });
}

function renderAdmin() {
  return render(
    <MemoryRouter initialEntries={['/admin']}>
      <Routes>
        <Route element={<AdminRoute />}>
          <Route path="/admin" element={<div>page admin</div>} />
        </Route>
        <Route path="/dashboard" element={<div>dashboard</div>} />
        <Route path="/login" element={<div>page login</div>} />
      </Routes>
    </MemoryRouter>
  );
}

describe('AdminRoute', () => {
  it("affiche le contenu si l'utilisateur est admin", () => {
    mockAuth({ id: 2, role: 'admin' }, true);
    renderAdmin();
    expect(screen.getByText('page admin')).toBeInTheDocument();
  });

  it('redirige vers /dashboard un utilisateur connecté non-admin', () => {
    mockAuth({ id: 1, role: 'user' }, false);
    renderAdmin();
    expect(screen.queryByText('page admin')).not.toBeInTheDocument();
    expect(screen.getByText('dashboard')).toBeInTheDocument();
  });

  it('redirige vers /dashboard si non connecté', () => {
    mockAuth(null, false);
    renderAdmin();
    expect(screen.queryByText('page admin')).not.toBeInTheDocument();
    expect(screen.getByText('dashboard')).toBeInTheDocument();
  });
});
