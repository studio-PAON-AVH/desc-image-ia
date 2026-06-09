import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '@/context/AuthContext';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

export function Navbar() {
  const { user, isAdmin, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    try {
      await logout();
      navigate('/login');
    } catch {
      // Logout failed silently — user stays on current page
    }
  };

  if (!user) return null;

  return (
    <nav className="border-b bg-background" role="navigation" aria-label="Navigation principale">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <div className="flex items-center gap-6">
          <Link to="/dashboard" className="text-lg font-semibold" aria-label="Accueil - Tableau de bord">
            Mission Apprentissage
          </Link>
          <div className="flex items-center gap-4">
            <Link to="/dashboard" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
              Tableau de bord
            </Link>
            <Link to="/upload" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
              Upload
            </Link>
            {isAdmin && (
              <Link to="/admin/tasks" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
                Admin
              </Link>
            )}
          </div>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-sm text-muted-foreground">{user.username}</span>
          {isAdmin && <Badge variant="secondary">Admin</Badge>}
          <Button variant="outline" size="sm" onClick={handleLogout}>
            Se deconnecter
          </Button>
        </div>
      </div>
    </nav>
  );
}
