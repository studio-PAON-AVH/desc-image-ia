import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { validateDescriptions, addDescriptions, getDescriptions } from '@/api/description';
import { getTask } from '@/api/task';
import type {
  IImage,
  IDescription,
  IDescriptionValidation,
  ITaskDescriptionsPayload,
  ITaskImageEntry,
} from '@/interfaces';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';

interface ImageValidationState {
  selectedDescriptionIndex: number | null;
  customText: string;
  selectedModelKey: string | null;
}

const MODEL_LABELS: Record<string, string> = {
  salesforce_blip: 'Salesforce BLIP',
  florence2: 'Florence 2',
  git_large: 'GIT Large',
};
const MODEL_KEYS = ['salesforce_blip', 'florence2', 'git_large'] as const;
type ModelKey = (typeof MODEL_KEYS)[number];

function extractDescriptionsPayload(
  result: unknown
): ITaskDescriptionsPayload | null {
  if (!result || typeof result !== 'object') return null;
  const r = result as Record<string, unknown>;
  if (r.images && typeof r.images === 'object') return result as ITaskDescriptionsPayload;
  if (r.descriptions && typeof r.descriptions === 'object') {
    return r.descriptions as ITaskDescriptionsPayload;
  }
  return null;
}

function taskPayloadToImages(payload: ITaskDescriptionsPayload): IImage[] {
  const entries = Object.values(payload.images) as ITaskImageEntry[];
  entries.sort((a, b) => a.index - b.index);
  return entries.map((entry) => {
    const descriptions: IDescription[] = [];
    MODEL_KEYS.forEach((key) => {
      const slot = entry[key];
      const text = slot?.french_description ?? slot?.description;
      if (text) {
        descriptions.push({
          description_id: entry.index * 10 + MODEL_KEYS.indexOf(key as ModelKey),
          description_text: text,
          model_name: MODEL_LABELS[key],
          model_key: key,
          validated_by_human: false,
        });
      }
    });
    return {
      image_id: entry.index,
      image_file_name: `image_${entry.index}`,
      image_position_in_epub: entry.index + 1,
      descriptions,
    };
  });
}

export function Descriptions() {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();
  const [images, setImages] = useState<IImage[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [validationStates, setValidationStates] = useState<Map<number, ImageValidationState>>(new Map());

  const [isTaskCompleted, setIsTaskCompleted] = useState(false);
  const [progress, setProgress] = useState<{ processed: number; total: number }>({
    processed: 0,
    total: 0,
  });

  useEffect(() => {
    if (!taskId) return;
    let cancelled = false;
    let intervalId: ReturnType<typeof setInterval> | null = null;

    const stopPolling = () => {
      if (intervalId) {
        clearInterval(intervalId);
        intervalId = null;
      }
    };

    const loadExistingFinals = async () => {
      try {
        const data = await getDescriptions(taskId);
        if (cancelled) return;
        setValidationStates((prev) => {
          const next = new Map(prev);
          data.images.forEach((img, index) => {
            if (!img.final_description) return;
            const existing = next.get(index);
            if (existing && existing.customText.trim() !== '') return;
            next.set(index, {
              selectedDescriptionIndex: null,
              customText: img.final_description.description_text,
              selectedModelKey: img.final_description.model_key,
            });
          });
          return next;
        });
      } catch {
        // pas de descriptions persistées encore, on ignore
      }
    };

    const fetchOnce = async () => {
      try {
        const data = await getTask(taskId);
        if (cancelled) return;

        setProgress({
          processed: data.processed_images ?? 0,
          total: data.total_images ?? 0,
        });

        const payload = extractDescriptionsPayload(data.result);
        const nextImages = payload ? taskPayloadToImages(payload) : [];
        setImages(nextImages);

        setValidationStates((prev) => {
          const next = new Map(prev);
          nextImages.forEach((img, index) => {
            const existing = next.get(index);
            if (!existing) {
              next.set(index, { selectedDescriptionIndex: null, customText: '', selectedModelKey: null });
              return;
            }
            if (existing.selectedDescriptionIndex === null && existing.selectedModelKey) {
              const matchIdx = img.descriptions.findIndex(
                (d) => d.model_key === existing.selectedModelKey,
              );
              if (matchIdx !== -1) {
                next.set(index, { ...existing, selectedDescriptionIndex: matchIdx });
              }
            }
          });
          return next;
        });

        setError('');
        if (data.status === 'completed') {
          setIsTaskCompleted(true);
          stopPolling();
        }
      } catch {
        if (!cancelled) setError('Impossible de charger les descriptions.');
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    };

    setIsLoading(true);
    loadExistingFinals();
    fetchOnce();
    intervalId = setInterval(fetchOnce, 3000);

    return () => {
      cancelled = true;
      stopPolling();
    };
  }, [taskId]);

  const updateValidationState = (imageIndex: number, update: Partial<ImageValidationState>) => {
    setValidationStates((prev) => {
      const next = new Map(prev);
      const current = next.get(imageIndex) ?? { selectedDescriptionIndex: null, customText: '', selectedModelKey: null };
      next.set(imageIndex, { ...current, ...update });
      return next;
    });
  };

  const handleSelectDescription = (imageIndex: number, descIndex: number) => {
    const image = images[imageIndex];
    const desc = image?.descriptions[descIndex];
    if (!desc) return;
    const current = validationStates.get(imageIndex);
    if (current?.selectedDescriptionIndex === descIndex) {
      updateValidationState(imageIndex, {
        selectedDescriptionIndex: null,
        customText: '',
        selectedModelKey: null,
      });
      return;
    }
    updateValidationState(imageIndex, {
      selectedDescriptionIndex: descIndex,
      customText: desc.description_text,
      selectedModelKey: desc.model_key,
    });
  };

  const handleCustomTextChange = (imageIndex: number, text: string) => {
    updateValidationState(imageIndex, { customText: text });
  };

  const buildValidations = (): IDescriptionValidation[] => {
    const validations: IDescriptionValidation[] = [];

    images.forEach((_image, imageIndex) => {
      const state = validationStates.get(imageIndex);
      if (!state) return;

      const text = state.customText.trim();
      if (!text) return;

      validations.push({
        image_index: imageIndex,
        text,
        model: state.selectedModelKey,
      });
    });

    return validations;
  };

  const handleValidateAll = async () => {
    if (!taskId) return;

    const validations = buildValidations();
    if (validations.length === 0) {
      setError('Veuillez selectionner ou ecrire une description pour chaque image.');
      return;
    }

    setIsSubmitting(true);
    setError('');

    try {
      await validateDescriptions(taskId, validations);
      const blob = await addDescriptions(taskId);

      // Trigger file download
      const url = window.URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = `epub_${taskId}.epub`;
      document.body.appendChild(anchor);
      anchor.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(anchor);

      navigate('/dashboard');
    } catch {
      setError('Une erreur est survenue lors de la validation. Veuillez reessayer.');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="h-8 w-64 animate-pulse rounded bg-muted" />
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="h-48 animate-pulse rounded bg-muted" />
        ))}
      </div>
    );
  }

  if (error && images.length === 0) {
    return (
      <div>
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
        <Button variant="outline" className="mt-4" onClick={() => navigate('/dashboard')}>
          Retour au tableau de bord
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Validation des descriptions</h1>
        <div className="flex items-center gap-2">
          <Badge variant="secondary">{images.length} images</Badge>
          {!isTaskCompleted && (
            <Badge variant="outline" className="animate-pulse">
              Generation en cours {progress.total > 0 ? `(${progress.processed}/${progress.total})` : ''}
            </Badge>
          )}
        </div>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {images.map((image, imageIndex) => {
        const state = validationStates.get(imageIndex);
        return (
          <Card key={image.image_id}>
            <CardHeader>
              <CardTitle className="text-lg">
                Image {image.image_position_in_epub} - {image.image_file_name}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-3 md:grid-cols-3">
                {image.descriptions.map((desc, descIndex) => {
                  const isSelected = state?.selectedDescriptionIndex === descIndex;
                  return (
                    <button
                      key={desc.description_id}
                      type="button"
                      onClick={() => handleSelectDescription(imageIndex, descIndex)}
                      className={`rounded-lg border p-4 text-left transition-colors ${
                        isSelected
                          ? 'border-primary bg-primary/5 ring-2 ring-primary'
                          : 'border-border hover:border-primary/50'
                      }`}
                      aria-pressed={isSelected}
                      aria-label={`Description par ${desc.model_name}: ${desc.description_text}`}
                    >
                      <div className="mb-2 flex items-center justify-between">
                        <Badge variant="outline">{desc.model_name}</Badge>
                        {isSelected && <Badge>Selectionne</Badge>}
                      </div>
                      <p className="text-sm">{desc.description_text}</p>
                    </button>
                  );
                })}
              </div>

              <div className="space-y-2">
                <Label htmlFor={`custom-${imageIndex}`}>
                  Ou ecrire une description personnalisee
                </Label>
                <Textarea
                  id={`custom-${imageIndex}`}
                  value={state?.customText ?? ''}
                  onChange={(e) => handleCustomTextChange(imageIndex, e.target.value)}
                  placeholder="Saisissez votre propre description..."
                  rows={3}
                />
              </div>
            </CardContent>
          </Card>
        );
      })}

      <div className="sticky bottom-4 flex gap-4">
        <Button variant="outline" onClick={() => navigate('/dashboard')} disabled={isSubmitting}>
          Annuler
        </Button>
        <Button
          className="flex-1"
          onClick={handleValidateAll}
          disabled={isSubmitting || !isTaskCompleted}
        >
          {isSubmitting
            ? 'Validation en cours...'
            : !isTaskCompleted
              ? 'En attente de la fin de la generation...'
              : 'Valider tout et telecharger'}
        </Button>
      </div>
    </div>
  );
}
