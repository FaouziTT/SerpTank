import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, X, FileText, Image, FileSpreadsheet, File } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { cn } from '@/lib/utils';

interface FileUploadProps {
  onUpload: (files: File[]) => void | Promise<void>;
  accept?: Record<string, string[]>;
  maxSize?: number;
  maxFiles?: number;
  className?: string;
  disabled?: boolean;
}

interface UploadedFile {
  file: File;
  progress: number;
  status: 'pending' | 'uploading' | 'completed' | 'error';
  error?: string;
}

export function FileUpload({
  onUpload,
  accept = {
    'image/*': ['.png', '.jpg', '.jpeg', '.gif', '.webp'],
    'text/csv': ['.csv'],
    'application/pdf': ['.pdf'],
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
    'application/vnd.ms-excel': ['.xls'],
  },
  maxSize = 10 * 1024 * 1024, // 10MB
  maxFiles = 5,
  className,
  disabled = false,
}: FileUploadProps) {
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      const newFiles = acceptedFiles.map(file => ({
        file,
        progress: 0,
        status: 'pending' as const,
      }));

      setUploadedFiles(prev => [...prev, ...newFiles]);

      // Simulate upload progress
      for (let i = 0; i < newFiles.length; i++) {
        const fileIndex = uploadedFiles.length + i;
        
        // Update status to uploading
        setUploadedFiles(prev => 
          prev.map((f, idx) => 
            idx === fileIndex ? { ...f, status: 'uploading' } : f
          )
        );

        // Simulate progress
        for (let progress = 0; progress <= 100; progress += 10) {
          await new Promise(resolve => setTimeout(resolve, 100));
          setUploadedFiles(prev => 
            prev.map((f, idx) => 
              idx === fileIndex ? { ...f, progress } : f
            )
          );
        }

        // Update status to completed
        setUploadedFiles(prev => 
          prev.map((f, idx) => 
            idx === fileIndex ? { ...f, status: 'completed' } : f
          )
        );
      }

      // Call the onUpload callback
      try {
        await onUpload(acceptedFiles);
      } catch (error) {
        // Handle upload error
        console.error('Upload error:', error);
      }
    },
    [uploadedFiles.length, onUpload]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept,
    maxSize,
    maxFiles,
    disabled,
  });

  const removeFile = (index: number) => {
    setUploadedFiles(prev => prev.filter((_, i) => i !== index));
  };

  const getFileIcon = (file: File) => {
    if (file.type.startsWith('image/')) return <Image className="h-4 w-4" aria-label="Image file" />;
    if (file.type === 'text/csv' || file.type.includes('spreadsheet')) return <FileSpreadsheet className="h-4 w-4" />;
    if (file.type === 'application/pdf') return <FileText className="h-4 w-4" />;
    return <File className="h-4 w-4" />;
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div className={className}>
      <div
        {...getRootProps()}
        className={cn(
          'relative rounded-lg border-2 border-dashed p-6 text-center hover:border-primary/50 transition-colors cursor-pointer',
          isDragActive && 'border-primary bg-primary/5',
          disabled && 'opacity-50 cursor-not-allowed'
        )}
      >
        <input {...getInputProps()} />
        <Upload className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
        {isDragActive ? (
          <p className="text-sm text-muted-foreground">Drop the files here...</p>
        ) : (
          <>
            <p className="text-sm font-medium mb-1">
              Drag & drop files here, or click to select
            </p>
            <p className="text-xs text-muted-foreground">
              Supports images, CSV, PDF, and Excel files (max {formatFileSize(maxSize)})
            </p>
          </>
        )}
      </div>

      {uploadedFiles.length > 0 && (
        <div className="mt-4 space-y-2">
          {uploadedFiles.map((uploadedFile, index) => (
            <div
              key={index}
              className="flex items-center justify-between p-3 rounded-lg border bg-card"
            >
              <div className="flex items-center space-x-3 flex-1">
                {getFileIcon(uploadedFile.file)}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">
                    {uploadedFile.file.name}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {formatFileSize(uploadedFile.file.size)}
                  </p>
                </div>
              </div>
              
              <div className="flex items-center space-x-2">
                {uploadedFile.status === 'uploading' && (
                  <div className="w-24">
                    <Progress value={uploadedFile.progress} className="h-2" />
                  </div>
                )}
                
                {uploadedFile.status === 'completed' && (
                  <span className="text-xs text-green-600 font-medium">Uploaded</span>
                )}
                
                {uploadedFile.status === 'error' && (
                  <span className="text-xs text-red-600 font-medium">Failed</span>
                )}
                
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => removeFile(index)}
                  className="h-8 w-8 p-0"
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}