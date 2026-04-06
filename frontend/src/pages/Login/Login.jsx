import React, { useState } from 'react';
import './Login.scss';
import PersonOutlineOutlinedIcon from '@mui/icons-material/PersonOutlineOutlined';
import LockOutlinedIcon from '@mui/icons-material/LockOutlined';
import VisibilityOffOutlinedIcon from '@mui/icons-material/VisibilityOffOutlined';
import VisibilityOutlinedIcon from '@mui/icons-material/VisibilityOutlined';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

// Axios instance with interceptors for auto-refresh
const api = axios.create({
	baseURL: 'http://localhost:8000',
});

// Add access token to requests
api.interceptors.request.use((config) => {
	const token = localStorage.getItem('access_token');
	if (token) config.headers['Authorization'] = `Bearer ${token}`;
	return config;
});

// Handle 401 errors by refreshing access token
api.interceptors.response.use(
	(response) => response,
	async (error) => {
		const originalRequest = error.config;

		if (
			error.response &&
			error.response.status === 401 &&
			!originalRequest._retry
		) {
			originalRequest._retry = true;
			const refreshToken = localStorage.getItem('refresh_token');

			if (refreshToken) {
				try {
					const res = await axios.post(
						'http://localhost:8000/auth/refresh',
						{
							refresh_token: refreshToken,
						},
					);

					localStorage.setItem('access_token', res.data.access_token);
					localStorage.setItem(
						'refresh_token',
						res.data.refresh_token,
					); // rotate refresh token

					originalRequest.headers['Authorization'] =
						'Bearer ' + res.data.access_token;
					return axios(originalRequest); // retry original request
				} catch (err) {
					// Refresh token expired or invalid → log out
					localStorage.clear();
					window.location.href = '/login';
					return Promise.reject(err);
				}
			} else {
				// No refresh token → log out
				localStorage.clear();
				window.location.href = '/login';
			}
		}

		return Promise.reject(error);
	},
);

export default function Login() {
	const navigate = useNavigate();

	const [username, setUsername] = useState('');
	const [password, setPassword] = useState('');
	const [showpassword, setShowPassword] = useState(false);
	const [error, setError] = useState('');

	const handleLogin = async (e) => {
		e.preventDefault();

		if (!username || !password) {
			setError('Username and password are required!');
			return;
		}

		try {
			const response = await api.post(
				'/auth/login',
				new URLSearchParams({ username, password }),
				{
					headers: {
						'Content-Type': 'application/x-www-form-urlencoded',
					},
				},
			);

			const {
				access_token,
				refresh_token,
				user_id,
				username: user,
			} = response.data;

			if (access_token && refresh_token) {
				localStorage.setItem('access_token', access_token);
				localStorage.setItem('refresh_token', refresh_token);
				localStorage.setItem('username', user);
				localStorage.setItem('user_id', user_id);
				navigate('/');
			} else {
				setError('Invalid credentials');
			}
		} catch (err) {
			if (err.response) {
				if (err.response.status === 401) {
					setError('Invalid username or password');
				} else {
					setError('Server error. Please try again later.');
				}
			} else {
				setError('Network error');
			}
		}
	};

	return (
		<div className='Login'>
			<div className='container'>
				<div className='header'>
					<h2>Log in to Solidify</h2>
					<span>Access your 3D conversion workplace.</span>
				</div>

				<form onSubmit={handleLogin}>
					<div className='fields'>
						<div className='username-field'>
							<label>Username</label>
							<div className='user-input'>
								<PersonOutlineOutlinedIcon
									className='person'
									fontSize='medium'
								/>
								<input
									type='text'
									placeholder='Enter your username'
									name='username'
									value={username}
									onChange={(e) =>
										setUsername(e.target.value)
									}
								/>
							</div>
						</div>

						<div className='password'>
							<label>Password</label>
							<div className='password-input'>
								<LockOutlinedIcon
									className='lock'
									fontSize='medium'
								/>
								<input
									type={showpassword ? 'text' : 'password'}
									placeholder='Password'
									name='password'
									value={password}
									onChange={(e) =>
										setPassword(e.target.value)
									}
								/>
								<span
									className='eye'
									onClick={() =>
										setShowPassword(!showpassword)
									}
								>
									{showpassword ? (
										<VisibilityOffOutlinedIcon />
									) : (
										<VisibilityOutlinedIcon />
									)}
								</span>
							</div>
							{error && <p style={{ color: 'red' }}>{error}</p>}
							<span>Forgot Password?</span>
						</div>
					</div>

					<button type='submit'>Login</button>
				</form>
			</div>
		</div>
	);
}
