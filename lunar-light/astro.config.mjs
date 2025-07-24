import { defineConfig } from 'astro/config';
import tailwind from '@astrojs/tailwind';

export default defineConfig({
  integrations: [tailwind()],
  server: {
    port: 4321,
    host: true
  },
  // Make Astro less strict about linting and formatting
  vite: {
    esbuild: {
      logOverride: { 'this-is-undefined-in-esm': 'silent' }
    }
  },
  compilerOptions: {
    strictNullChecks: false,
    strict: false
  }
});
