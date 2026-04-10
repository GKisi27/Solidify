import React, { useState } from 'react';
import './Login.scss';
import PersonOutlineOutlinedIcon from '@mui/icons-material/PersonOutlineOutlined';
import LockOutlinedIcon from '@mui/icons-material/LockOutlined';
import VisibilityOffOutlinedIcon from '@mui/icons-material/VisibilityOffOutlined';
import VisibilityOutlinedIcon from '@mui/icons-material/VisibilityOutlined';
import { useNavigate } from 'react-router-dom';
import { storeAuthTokens } from '../../auth';

// Import the api instance you just created!
// Make sure to adjust the path depending on where api.js is located relative to Login.jsx
import api from '../../api';

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
			// Using the shared api instance
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
				storeAuthTokens({
					accessToken: access_token,
					refreshToken: refresh_token,
					username: user,
					userId: user_id,
				});
				navigate('/');
			} else {
				setError('Invalid credentials');
			}
		} catch (err) {
			if (err.response) {
				setError(
					err.response.status === 401
						? 'Invalid username or password'
						: 'Server error. Please try again later.',
				);
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
									autoComplete='username'
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
									autoComplete='current-password'
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
						</div>
					</div>
					<button type='submit'>Login</button>
				</form>
			</div>
		</div>
	);
}
