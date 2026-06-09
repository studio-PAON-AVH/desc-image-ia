import { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getMyTasks } from '@/api/auth';
import type { ITask } from '@/interfaces';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';

const STATUS_LABELS: Record<string, string> = {
  pending: 'En attente',
  in_progress: 'En cours',
  completed: 'Termine',
  failed: 'Echoue',
};

export function TaskStatus() {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();
  const [task, setTask] = useState<ITask | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!taskId) return;

    let cancelled = false;

    const fetchTask = async () => {
      try {
        const tasks = await getMyTasks();
        if (cancelled) return;

        const found = tasks.find((t) => t.task_id_redis === taskId) ?? null;
        setTask(found);
        setIsLoading(false);
        setError('');

        if (found && (found.status === 'completed' || found.status === 'failed')) {
          if (intervalRef.current) {
            clearInterval(intervalRef.current);
            intervalRef.current = null;
          }
        }
      } catch {
        if (cancelled) return;
        setError('Impossible de recuperer le statut de la tache.');
        setIsLoading(false);
      }
    };

    fetchTask();
    intervalRef.current = setInterval(fetchTask, 3000);

    return () => {
      cancelled = true;
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [taskId]);

  if (isLoading) {
    return (
      <div className="mx-auto max-w-2xl space-y-4">
        <div className="h-8 w-48 animate-pulse rounded bg-muted" />
        <div className="h-40 animate-pulse rounded bg-muted" />
      </div>
    );
  }

  if (error && !task) {
    return (
      <div className="mx-auto max-w-2xl">
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
        <Button variant="outline" className="mt-4" onClick={() => navigate('/dashboard')}>
          Retour au tableau de bord
        </Button>
      </div>
    );
  }

  if (!task) return null;

  const progressPercent =
    task.total_images > 0
      ? Math.round((task.processed_images / task.total_images) * 100)
      : 0;

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Statut de la tache</h1>
        <Badge
          variant={
            task.status === 'failed'
              ? 'destructive'
              : task.status === 'completed'
                ? 'default'
                : 'secondary'
          }
          className={task.status === 'in_progress' ? 'animate-pulse' : ''}
        >
          {STATUS_LABELS[task.status] ?? task.status}
        </Badge>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Progression du traitement</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex justify-between text-sm text-muted-foreground">
            <span>Images traitees</span>
            <span>
              {task.processed_images} / {task.total_images}
            </span>
          </div>
          <Progress value={progressPercent} aria-label={`${progressPercent}% complete`} />

          {(task.epubs?.length ?? 0) > 0 && (
            <div className="text-sm text-muted-foreground">
              <span className="font-medium">Fichier : </span>
              {task.epubs![0].file_name}
            </div>
          )}

          {error && (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {task.status !== 'completed' && task.status !== 'failed' && (
            <Button
              variant="outline"
              className="w-full"
              onClick={() => navigate(`/task/${taskId}/descriptions`)}
            >
              Prévisualiser les descriptions
            </Button>
          )}

          {task.status === 'completed' && (
            <Button className="w-full" onClick={() => navigate(`/task/${taskId}/descriptions`)}>
              Valider les descriptions
            </Button>
          )}

          {task.status === 'failed' && (
            <div className="space-y-3">
              <Alert variant="destructive">
                <AlertDescription>
                  Le traitement a echoue. Vous pouvez reessayer en uploadant a nouveau le fichier.
                </AlertDescription>
              </Alert>
              <Button variant="outline" className="w-full" onClick={() => navigate('/upload')}>
                Reessayer
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      <Button variant="outline" onClick={() => navigate('/dashboard')}>
        Retour au tableau de bord
      </Button>
    </div>
  );
}
