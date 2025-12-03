import React, { useCallback, useState } from 'react';
import { Upload } from 'lucide-react';
import { cn } from '../lib/utils';

interface FileUploadZoneProps {
  onFileSelect: (file: File) => void;
  acceptedTypes?: string[];
  className?: string;
  label?: string;
}

export default function FileUploadZone({
  onFileSelect,
  acceptedTypes = ['.csv', '.xlsx', '.xls'],
  className,
  label = 'Drag on-drop et une mappier en Excel/CSV',
}: FileUploadZoneProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [fileName, setFileName] = useState<string | null>(null);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);

      const file = e.dataTransfer.files[0];
      if (file) {
        setFileName(file.name);
        onFileSelect(file);
      }
    },
    [onFileSelect]
  );

  const handleFileInput = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) {
        setFileName(file.name);
        onFileSelect(file);
      }
    },
    [onFileSelect]
  );

  return (
    <div
      className={cn(
        'border-2 border-dashed rounded-lg p-8 text-center transition-colors cursor-pointer',
        isDragging
          ? 'border-teal-500 bg-teal-50'
          : 'border-slate-300 hover:border-slate-400',
        className
      )}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      onClick={() => document.getElementById('file-input')?.click()}
    >
      <input
        id="file-input"
        type="file"
        className="hidden"
        accept={acceptedTypes.join(',')}
        onChange={handleFileInput}
      />
      <Upload className="mx-auto h-8 w-8 text-slate-400 mb-3" />
      {fileName ? (
        <p className="text-sm text-teal-600 font-medium">{fileName}</p>
      ) : (
        <p className="text-sm text-slate-500">{label}</p>
      )}
    </div>
  );
}
