export function isTokenExpired(token) {
	try {
		const payload = JSON.parse(atob(token.split('.')[1]));
		const now = Math.floor(Date.now() / 1000);
		return payload.exp < now;
	} catch {
		return true;
	}
}

export function getStoredAccessToken() {
	return (
		localStorage.getItem('access_token') || localStorage.getItem('token')
	);
}

export function storeAuthTokens({
	accessToken,
	refreshToken,
	username,
	userId,
}) {
	localStorage.setItem('access_token', accessToken);
	localStorage.setItem('token', accessToken);
	if (refreshToken !== undefined && refreshToken !== null) {
		localStorage.setItem('refresh_token', refreshToken);
	}

	if (username) {
		localStorage.setItem('username', username);
	}

	if (userId !== undefined && userId !== null) {
		localStorage.setItem('user_id', String(userId));
	}
}
