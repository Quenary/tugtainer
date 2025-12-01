/**
 * Get from storage (deserialized)
 * @param key key
 * @param storage storage
 * @default localStorage
 * @returns
 */
export const storageGetItemJson = <T extends unknown = unknown>(
  key: string,
  storage: Storage = localStorage,
): T | null => {
  const value = storage.getItem(key);
  if (value) {
    try {
      return JSON.parse(value);
    } catch (e) {
      console.error(e);
      console.warn(`Invalid key '${key}' removed from storage`);
      localStorage.removeItem(key);
      return null;
    }
  }
  return null;
};

/**
 * Save to storage (serialize)
 * @param key key
 * @param value value
 * @param storage storage
 * @default localStorage
 */
export const storageSetItemJson = <T extends unknown = unknown>(
  key: string,
  value: T,
  storage: Storage = localStorage,
): void => {
  storage.setItem(key, JSON.stringify(value));
};
