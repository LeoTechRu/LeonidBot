import { defineConfig } from 'vite';

export default defineConfig({
  root: '.',
  build: {
    outDir: 'static',
    rollupOptions: {
      input: 'src/main.ts'
    },
    emptyOutDir: false
  }
});
