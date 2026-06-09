import { useState, useRef, type FormEvent, type ChangeEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { uploadEpub } from '@/api/epub';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import axios from 'axios';

export function Upload() {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState('');

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    setError('');
    const selected = e.target.files?.[0] ?? null;

    if (selected && !selected.name.toLowerCase().endsWith('.epub')) {
      setError('Veuillez selectionner un fichier au format EPUB.');
      setFile(null);
      if (fileInputRef.current) fileInputRef.current.value = '';
      return;
    }

    setFile(selected);
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!file) {
      setError('Veuillez selectionner un fichier.');
      return;
    }

    setError('');
    setIsUploading(true);
    setUploadProgress(0);

    try {
      const { task_id } = await uploadEpub(file, (progressEvent) => {
        if (progressEvent.total) {
          const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          setUploadProgress(percent);
        }
      });
      navigate(`/task/${task_id}`);
    } catch (err) {
      if (axios.isAxiosError(err)) {
        const status = err.response?.status;
        if (status === 413) {
          setError('Le fichier est trop volumineux. Veuillez en choisir un plus petit.');
        } else if (status === 415) {
          setError('Format de fichier non supporte. Veuillez uploader un fichier EPUB.');
        } else if (status === 422) {
          setError('Le fichier ne semble pas etre un EPUB valide.');
        } else {
          setError("Une erreur est survenue lors de l'upload. Veuillez reessayer.");
        }
      } else {
        setError('Impossible de se connecter au serveur. Verifiez votre connexion internet.');
      }
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="mx-auto max-w-2xl">
      <Card>
        <CardHeader>
          <CardTitle>Uploader un EPUB</CardTitle>
          <CardDescription>
            Selectionnez un fichier EPUB pour generer automatiquement des descriptions d'images.
          </CardDescription>
        </CardHeader>
        <form onSubmit={handleSubmit}>
          <CardContent className="space-y-6">
            {error && (
              <Alert variant="destructive">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            <div className="space-y-2">
              <Label htmlFor="epub-file">Fichier EPUB</Label>
              <Input
                ref={fileInputRef}
                id="epub-file"
                type="file"
                accept=".epub"
                onChange={handleFileChange}
                disabled={isUploading}
                aria-describedby="file-hint"
              />
              <p id="file-hint" className="text-xs text-muted-foreground">
                Seuls les fichiers .epub sont acceptes.
              </p>
            </div>

            {isUploading && (
              <div className="space-y-2" role="status" aria-label="Upload en cours">
                <div className="flex justify-between text-sm">
                  <span>Upload en cours...</span>
                  <span>{uploadProgress}%</span>
                </div>
                <Progress value={uploadProgress} />
              </div>
            )}

            <Button type="submit" className="w-full" disabled={isUploading || !file}>
              {isUploading ? 'Upload en cours...' : 'Uploader'}
            </Button>
          </CardContent>
        </form>
      </Card>
    </div>
  );
}
