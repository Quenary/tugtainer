/**
 * Checks whether value is premitive
 * @param value value
 * @returns
 */
export const isPremitive = (
  value: unknown,
): value is number | BigInt | string | boolean | symbol | undefined | null => {
  return value === null || !['object', 'function'].includes(typeof value);
};
