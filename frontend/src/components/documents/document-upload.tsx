'use client';

import { useRef, useState } from 'react';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { useUploadDocument } from '@/hooks/use-documents';
import { ApiRequestError } from '@/services/api-client';

interface UploadItem {
  id: string;
  filename: string;
  progress: number;
  status: 'uploading' | 'done' | 'error';
  error?: string;
}

export function DocumentUpload({ repositoryId }: { repositoryId: string }) {
  const [isDraggingOver, setIsDraggingOver] = useState(false);
  const [uploads, setUploads] = useState<UploadItem[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);
  const uploadDocument = useUploadDocument(repositoryId);

  function updateUpload(id: string, patch: Partial<UploadItem>) {
    setUploads((prev) => prev.map((item) => (item.id === id ? { ...item, ...patch } : item)));
  }

  async function uploadFiles(files: FileList | File[]) {
    for (const file of Array.from(files)) {
      const id = `${file.name}-${Date.now()}-${Math.random()}`;
      setUploads((prev) => [
        ...prev,
        { id, filename: file.name, progress: 0, status: 'uploading' },
      ]);

      try {
        await uploadDocument.mutateAsync({
          file,
          onProgress: (percent) => updateUpload(id, { progress: percent }),
        });
        updateUpload(id, { progress: 100, status: 'done' });
      } catch (err) {
        updateUpload(id, {
          status: 'error',
          error: err instanceof ApiRequestError ? err.message : 'Upload failed.',
        });
      }
    }
  }

  function handleDrop(event: React.DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setIsDraggingOver(false);
    if (event.dataTransfer.files.length > 0) void uploadFiles(event.dataTransfer.files);
  }

  function handleFileInputChange(event: React.ChangeEvent<HTMLInputElement>) {
    if (event.target.files && event.target.files.length > 0) void uploadFiles(event.target.files);
    event.target.value = '';
  }

  return (
    <div className="space-y-3">
      <div
        role="button"
        tabIndex={0}
        data-testid="document-upload-dropzone"
        onClick={() => inputRef.current?.click()}
        onKeyDown={(event) => {
          if (event.key === 'Enter' || event.key === ' ') inputRef.current?.click();
        }}
        onDragOver={(event) => {
          event.preventDefault();
          setIsDraggingOver(true);
        }}
        onDragLeave={() => setIsDraggingOver(false)}
        onDrop={handleDrop}
        className={`flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed p-6 text-center transition-colors ${
          isDraggingOver ? 'border-ring bg-muted' : 'border-border'
        }`}
      >
        <p className="text-sm font-medium">Drag and drop files here, or click to browse</p>
        <p className="text-muted-foreground mt-1 text-xs">
          PDF, DOCX, TXT, MD, CSV, HTML, JSON, XML — up to 500 MB
        </p>
        <input
          ref={inputRef}
          type="file"
          multiple
          className="sr-only"
          onChange={handleFileInputChange}
          data-testid="document-upload-input"
        />
      </div>

      {uploads.length > 0 && (
        <ul className="space-y-2" data-testid="document-upload-progress-list">
          {uploads.map((item) => (
            <li key={item.id} className="space-y-1">
              <div className="flex items-center justify-between text-xs">
                <span className="truncate">{item.filename}</span>
                <span className="text-muted-foreground">
                  {item.status === 'done'
                    ? 'Done'
                    : item.status === 'error'
                      ? 'Failed'
                      : `${item.progress}%`}
                </span>
              </div>
              <div className="bg-muted h-1.5 w-full overflow-hidden rounded-full">
                <div
                  className={`h-full rounded-full transition-all ${
                    item.status === 'error' ? 'bg-destructive' : 'bg-primary'
                  }`}
                  style={{ width: `${item.progress}%` }}
                />
              </div>
              {item.status === 'error' && (
                <Alert variant="destructive" className="py-2">
                  <AlertDescription className="text-xs">{item.error}</AlertDescription>
                </Alert>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
