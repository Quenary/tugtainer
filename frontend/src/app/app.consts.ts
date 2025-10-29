/**
 * Enum of useful regexp
 */
export const ERegexp = {
  /**
   * At least 8 chars
   * 1 upper case char
   * 1 lower case char
   * 1 num
   */
  password: /(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,64}/,
};
/**
 * Url to tugtainer deploy guideline
 */
export const DeployGuidelineUrl = 'https://github.com/Quenary/tugtainer?tab=readme-ov-file#deploy';
