/**
 * Labels publishers use for a source repository URL.
 * OCI is the current standard; label-schema is its predecessor.
 */
const SOURCE_LABELS = [
  'org.opencontainers.image.source',
  'org.label-schema.vcs-url',
] as const;

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null && !Array.isArray(value);

const isHttpUrl = (value: string): boolean => {
  try {
    const url = new URL(value);
    return url.protocol === 'http:' || url.protocol === 'https:';
  } catch {
    return false;
  }
};

const readLabels = (inspect: unknown): Record<string, unknown> | null => {
  if (!isRecord(inspect)) {
    return null;
  }
  const config = inspect['config'] ?? inspect['Config'];
  if (!isRecord(config)) {
    return null;
  }
  const labels = config['labels'] ?? config['Labels'];
  if (!isRecord(labels)) {
    return null;
  }
  return labels;
};

/**
 * Source repository URL from image/container inspect labels, if any.
 */
export const getImageSourceUrl = (inspect: unknown): string | null => {
  const labels = readLabels(inspect);
  if (!labels) {
    return null;
  }
  for (const key of SOURCE_LABELS) {
    const raw = labels[key];
    if (typeof raw !== 'string') {
      continue;
    }
    const value = raw.trim();
    if (value && isHttpUrl(value)) {
      return value;
    }
  }
  return null;
};
