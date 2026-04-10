import axios from 'axios';

const api = axios.create({
	baseURL: '/api',
});

api.interceptors.request.use((config) => {
	const token = localStorage.getItem('access_token');
	if (token && !config.url.includes('/auth/refresh')) {
		config.headers['Authorization'] = `Bearer ${token}`;
	}
	return config;
});

api.interceptors.response.use(
	(response) => response,
	async (error) => {
		const originalRequest = error.config;
		if (error.response?.status === 401 && !originalRequest._retry) {
			originalRequest._retry = true;
			const refreshToken = localStorage.getItem('refresh_token');
			if (!refreshToken) {
				localStorage.clear();
				window.location.href = '/login';
				return Promise.reject(error);
			}
			try {
				// We use axios here to avoid the interceptor loop
				const res = await axios.post('/api/auth/refresh', {
					refresh_token: refreshToken,
				});
				localStorage.setItem('access_token', res.data.access_token);
				localStorage.setItem('refresh_token', res.data.refresh_token);
				originalRequest.headers['Authorization'] =
					`Bearer ${res.data.access_token}`;
				return api(originalRequest);
			} catch (err) {
				localStorage.clear();
				window.location.href = '/login';
				return Promise.reject(err);
			}
		}
		return Promise.reject(error);
	},
);

export default api;
