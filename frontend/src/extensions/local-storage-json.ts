import { storageGetItemJson, storageSetItemJson } from '../app/shared/functions/storage.function';

declare global {
  interface Storage {
    /**
     * Get from storage (deserialized)
     * @param key key
     */
    getItemJson<T extends unknown = unknown>(key: string): T | null;
    /**
     * Save to storage (serialize)
     * @param key key
     * @param value value
     */
    setItemJson<T extends unknown = unknown>(key: string, value: T): void;
  }
}

export const storageJson = () => {
  Storage.prototype.getItemJson = (key) => storageGetItemJson(key, this);
  Storage.prototype.setItemJson = (key, value) => storageSetItemJson(key, value, this);
};
