// @ts-check
const eslint = require('@eslint/js');
const { defineConfig } = require('eslint/config');
const tseslint = require('typescript-eslint');
/** @type {import('eslint-plugin-playwright').default} */
const playwright = require('eslint-plugin-playwright');

module.exports = defineConfig([
  {
    ignores: [
      'node_modules/**',
      'test-results/**',
      'playwright-report/**',
      'blob-report/**',
    ],
  },
  {
    files: ['**/*.ts'],
    extends: [
      eslint.configs.recommended,
      tseslint.configs.recommended,
      tseslint.configs.stylistic,
    ],
    rules: {
      '@typescript-eslint/no-unused-vars': [
        'error',
        {
          argsIgnorePattern: '^_',
          varsIgnorePattern: '^_',
          caughtErrorsIgnorePattern: '^_',
        },
      ],
    },
  },
  {
    ...playwright.configs['flat/recommended'],
    files: ['integration/**/*.ts', 'e2e/**/*.ts'],
  },
]);
