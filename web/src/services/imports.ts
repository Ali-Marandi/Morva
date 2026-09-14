import { apiClient } from './api';

export interface ImportSource {
  sourceKey: string;
  fileName: string;
  category: string;
  categoryLabel: string;
  sheetName: string;
  headers: string[];
  importedAt: string;
  recordCount: number;
}

export interface ImportSummary {
  categories: Record<string, string>;
  totals: Record<string, number>;
  sources: ImportSource[];
}

export interface UploadResult {
  message: string;
  imported: Omit<ImportSource, 'sourceKey' | 'sheetName' | 'importedAt'> & { headers: string[] };
}

export const importService = {
  getSummary: () => apiClient.get<ImportSummary>('/imports/summary'),
  upload: (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return apiClient.upload<UploadResult>('/imports/upload', formData);
  },
};
