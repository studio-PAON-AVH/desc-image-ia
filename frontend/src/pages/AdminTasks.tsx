import { useEffect, useState } from 'react';
import { getAdminTasks } from '@/api/task';
import type { ITask } from '@/interfaces';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Alert, AlertDescription } from '@/components/ui/alert';

const STATUS_LABELS: Record<string, string> = {
  pending: 'En attente',
  in_progress: 'En cours',
  completed: 'Termine',
  failed: 'Echoue',
};

const STATUS_VARIANTS: Record<string, 'default' | 'secondary' | 'destructive' | 'outline'> = {
  pending: 'outline',
  in_progress: 'secondary',
  completed: 'default',
  failed: 'destructive',
};

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '-';
  return new Date(dateStr).toLocaleDateString('fr-FR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

const PAGE_SIZE = 50;

export function AdminTasks() {
  const [tasks, setTasks] = useState<ITask[]>([]);
  const [offset, setOffset] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [hasMore, setHasMore] = useState(true);

  const fetchTasks = (newOffset: number) => {
    setIsLoading(true);
    setError('');
    getAdminTasks(PAGE_SIZE, newOffset)
      .then((data) => {
        setTasks(data.tasks);
        setOffset(newOffset);
        setHasMore(data.tasks.length === PAGE_SIZE);
      })
      .catch(() => {
        setError('Impossible de charger les taches. Veuillez reessayer.');
      })
      .finally(() => {
        setIsLoading(false);
      });
  };

  useEffect(() => {
    fetchTasks(0);
  }, []);

  if (isLoading && tasks.length === 0) {
    return (
      <div className="space-y-4">
        <div className="h-8 w-64 animate-pulse rounded bg-muted" />
        <div className="space-y-2">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="h-12 animate-pulse rounded bg-muted" />
          ))}
        </div>
      </div>
    );
  }

  if (error && tasks.length === 0) {
    return (
      <div>
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
        <Button variant="outline" className="mt-4" onClick={() => fetchTasks(0)}>
          Reessayer
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Administration - Toutes les taches</h1>

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {tasks.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-lg border border-dashed p-12 text-center">
          <p className="text-lg font-medium text-muted-foreground">Aucune tache</p>
        </div>
      ) : (
        <div className="rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID Tache</TableHead>
                <TableHead>Fichier</TableHead>
                <TableHead>Statut</TableHead>
                <TableHead>Progression</TableHead>
                <TableHead>Cree le</TableHead>
                <TableHead>Demarre le</TableHead>
                <TableHead>Termine le</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {tasks.map((task) => (
                <TableRow key={task.task_id_redis}>
                  <TableCell className="font-mono text-xs">
                    {task.task_id_redis.substring(0, 8)}...
                  </TableCell>
                  <TableCell className="font-medium">
                    {task.epubs?.[0]?.file_name ?? 'N/A'}
                  </TableCell>
                  <TableCell>
                    <Badge variant={STATUS_VARIANTS[task.status] ?? 'outline'}>
                      {STATUS_LABELS[task.status] ?? task.status}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    {task.processed_images} / {task.total_images}
                  </TableCell>
                  <TableCell>{formatDate(task.created_at)}</TableCell>
                  <TableCell>{formatDate(task.started_at)}</TableCell>
                  <TableCell>{formatDate(task.completed_at)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      <div className="flex justify-between">
        <Button
          variant="outline"
          disabled={offset === 0 || isLoading}
          onClick={() => fetchTasks(Math.max(0, offset - PAGE_SIZE))}
        >
          Precedent
        </Button>
        <span className="self-center text-sm text-muted-foreground">
          Page {Math.floor(offset / PAGE_SIZE) + 1}
        </span>
        <Button
          variant="outline"
          disabled={!hasMore || isLoading}
          onClick={() => fetchTasks(offset + PAGE_SIZE)}
        >
          Suivant
        </Button>
      </div>
    </div>
  );
}
