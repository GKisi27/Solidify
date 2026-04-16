import axios from 'axios';

export function storeAuthTokens({ accessToken, refreshToken, username, userId }) {
    localStorage.setItem('access_token', accessToken); // only this, remove 'token'
    if (refreshToken != null) localStorage.setItem('refresh_token', refreshToken);
    if (username) localStorage.setItem('username', username);
    if (userId != null) localStorage.setItem('user_id', String(userId));
}

export function getStoredAccessToken() {
    return localStorage.getItem('access_token');
}

export function isTokenExpired(token) {
    try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        return payload.exp < Math.floor(Date.now() / 1000);
    } catch {
        return true;
    }
}

// src/auth.js - add this function
export async function ensureAuth() {
    const accessToken = localStorage.getItem('access_token');
    const refreshToken = localStorage.getItem('refresh_token');

    if (!refreshToken) return false; // no way to recover, must login

    if (!accessToken || isTokenExpired(accessToken)) {
        // try to silently refresh before the app loads
        try {
            const res = await axios.post('/api/auth/refresh', { refresh_token: refreshToken });
            localStorage.setItem('access_token', res.data.access_token);
            localStorage.setItem('refresh_token', res.data.refresh_token);
            return true;
        } catch {
            localStorage.clear();
            return false;
        }
    }

    return true;
}

export function startTokenRefreshTimer() {
    setInterval(async () => {
        const accessToken = localStorage.getItem('access_token');
        const refreshToken = localStorage.getItem('refresh_token');

        if (!refreshToken) return;

        if (!accessToken || isTokenExpired(accessToken)) {
            try {
                const res = await axios.post('/api/auth/refresh', { refresh_token: refreshToken });
                localStorage.setItem('access_token', res.data.access_token);
                localStorage.setItem('refresh_token', res.data.refresh_token);
            } catch {
                localStorage.clear();
                window.location.href = '/login';
            }
        }
    }, 60 * 1000); // checks every 60 seconds
}