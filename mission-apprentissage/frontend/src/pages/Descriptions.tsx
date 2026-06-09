import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getDescriptions, validateDescriptions, addDescriptions } from '@/api/description';
import type { IImage, IDescriptionValidation } from '@/interfaces';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';

interface ImageValidationState {
  selectedDescriptionIndex: number | null;
  customText: string;
}

export function Descriptions() {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();
  const [images, setImages] = useState<IImage[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [validationStates, setValidationStates] = useState<Map<number, ImageValidationState>>(new Map());

  useEffect(() => {
    if (!taskId) return;
    let cancelled = false;

    setIsLoading(true);
    getDescriptions(taskId)
      .then((data) => {
        if (cancelled) return;
        setImages(data.images);
        const initialStates = new Map<number, ImageValidationState>();
        data.images.forEach((_img, index) => {
          initialStates.set(index, { selectedDescriptionIndex: null, customText: '' });
        });
        setValidationStates(initialStates);
      })
      .catch(() => {
        if (!cancelled) setError('Impossible de charger les descriptions.');
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });

    return () => { cancelled = true; };
  }, [taskId]);

  const updateValidationState = (imageIndex: number, update: Partial<ImageValidationState>) => {
    setValidationStates((prev) => {
      const next = new Map(prev);
      const current = next.get(imageIndex) ?? { selectedDescriptionIndex: null, customText: '' };
      next.set(imageIndex, { ...current, ...update });
      return next;
    });
  };

  const handleSelectDescription = (imageIndex: number, descIndex: number) => {
    updateValidationState(imageIndex, { selectedDescriptionIndex: descIndex, customText: '' });
  };

  const handleCustomTextChange = (imageIndex: number, text: string) => {
    updateValidationState(imageIndex, { customText: text, selectedDescriptionIndex: null });
  };

  const buildValidations = (): IDescriptionValidation[] => {
    const validations: IDescriptionValidation[] = [];

    images.forEach((image, imageIndex) => {
      const state = validationStates.get(imageIndex);
      if (!state) return;

      if (state.customText.trim()) {
        validations.push({
          image_index: imageIndex,
          text: state.customText.trim(),
          is_written_by_ai: false,
          is_written_by_human: true,
        });
      } else if (state.selectedDescriptionIndex !== null) {
        const desc = image.descriptions[state.selectedDescriptionIndex];
        if (desc) {
          validations.push({
            image_index: imageIndex,
            text: desc.description_text,
            model: desc.model_key,
            is_written_by_ai: true,
            is_written_by_human: false,
          });
        }
      }
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
        <Badge variant="secondary">{images.length} images</Badge>
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
        <Button className="flex-1" onClick={handleValidateAll} disabled={isSubmitting}>
          {isSubmitting ? 'Validation en cours...' : 'Valider tout et telecharger'}
        </Button>
      </div>
    </div>
  );
}
