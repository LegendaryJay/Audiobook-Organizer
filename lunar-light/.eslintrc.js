module.exports = {
  extends: ['eslint:recommended'],
  env: {
    browser: true,
    es2022: true,
    node: true,
  },
  parserOptions: {
    ecmaVersion: 'latest',
    sourceType: 'module',
  },
  rules: {
    // Disable strict rules that are too aggressive
    'no-unused-vars': 'warn',
    'no-undef': 'warn',
    'no-console': 'off',
    'no-debugger': 'warn',
    'no-empty': 'warn',
    'no-constant-condition': 'warn',
    'no-unreachable': 'warn',
    
    // Allow common patterns
    'no-implicit-globals': 'off',
    'no-var': 'off',
    'prefer-const': 'warn',
    'no-redeclare': 'warn',
    
    // Be lenient with script tags in Astro components
    'no-inner-declarations': 'off',
  },
  globals: {
    // Allow common browser globals
    'window': 'readonly',
    'document': 'readonly',
    'console': 'readonly',
    'fetch': 'readonly',
    'EventSource': 'readonly',
    'localStorage': 'readonly',
    'sessionStorage': 'readonly',
  },
  overrides: [
    {
      files: ['*.astro'],
      parser: '@astrojs/compiler',
      rules: {
        // Even more lenient for Astro files
        'no-unused-vars': 'off',
        'no-undef': 'off',
      },
    },
  ],
};
