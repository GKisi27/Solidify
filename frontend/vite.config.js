import path from 'path';
import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [react(), tailwindcss()],
	resolve: {
		alias: {
			'@': path.resolve('./src'),
		},
	},
	server: {
		host: true,
		proxy: {
			'/api': {
				target: 'http://backend:8000',
				changeOrigin: true,
				rewrite: (path) => path.replace(/^\/api/, ''),
			},
		},
	},
});
