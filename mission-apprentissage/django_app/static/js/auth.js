// JWT token helpers
function getAccessToken() {
    return localStorage.getItem('access_token');
}

function getRefreshToken() {
    return localStorage.getItem('refresh_token');
}

function setTokens(access, refresh) {
    localStorage.setItem('access_token', access);
    localStorage.setItem('refresh_token', refresh);
}

function clearTokens() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
}

function redirectToLogin() {
    clearTokens();
    const next = encodeURIComponent(window.location.pathname + window.location.search);
    window.location.href = '/login/?next=' + next;
}

async function refreshAccessToken() {
    const refreshToken = getRefreshToken();
    if (!refreshToken) return false;

    try {
        const response = await fetch(`${FASTAPI_URL}/api/auth/refresh`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ refresh_token: refreshToken }),
        });

        if (!response.ok) return false;

        const data = await response.json();
        if (data.access_token) {
            localStorage.setItem('access_token', data.access_token);
            if (data.refresh_token) {
                localStorage.setItem('refresh_token', data.refresh_token);
            }
            return true;
        }
        return false;
    } catch {
        return false;
    }
}

async function fetchWithAuth(url, options = {}) {
    const token = getAccessToken();
    if (!token) {
        redirectToLogin();
        return null;
    }

    const headers = {
        ...(options.headers || {}),
        'Authorization': `Bearer ${token}`,
    };

    let response = await fetch(url, { ...options, headers });

    if (response.status === 401) {
        const refreshed = await refreshAccessToken();
        if (!refreshed) {
            redirectToLogin();
            return null;
        }
        headers['Authorization'] = `Bearer ${getAccessToken()}`;
        response = await fetch(url, { ...options, headers });
    }

    return response;
}

async function logout() {
    const token = getAccessToken();
    if (token) {
        try {
            const refreshToken = getRefreshToken();
            await fetch(`${FASTAPI_URL}/api/auth/logout`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`,
                },
                body: JSON.stringify({ refresh_token: refreshToken }),
            });
        } catch {
            // best-effort
        }
    }
    clearTokens();
    window.location.href = '/login/';
}

// Register form handler
if (document.getElementById('registerForm')) {
    document.getElementById('registerForm').addEventListener('submit', async function(e) {
        e.preventDefault();
        const username = document.getElementById('registerUsername').value;
        const email = document.getElementById('registerEmail').value;
        const password = document.getElementById('registerPassword').value;
        const errorDiv = document.getElementById('registerError');
        errorDiv.style.display = 'none';

        try {
            const response = await fetch(`${FASTAPI_URL}/api/auth/register`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, email, password }),
            });
            const data = await response.json();
            if (response.ok && data.access_token) {
                setTokens(data.access_token, data.refresh_token || '');
                window.location.href = '/process/';
            } else {
                errorDiv.textContent = data.detail || 'Erreur lors de l\'inscription';
                errorDiv.style.display = 'block';
            }
        } catch {
            errorDiv.textContent = 'Erreur de connexion au serveur';
            errorDiv.style.display = 'block';
        }
    });
}

// Login form handler
if (document.getElementById('loginForm')) {
    document.getElementById('loginForm').addEventListener('submit', async function(e) {
        e.preventDefault();

        const email = document.getElementById('loginEmail').value;
        const password = document.getElementById('loginPassword').value;
        const errorDiv = document.getElementById('loginError');

        errorDiv.style.display = 'none';

        try {
            const response = await fetch(`${FASTAPI_URL}/api/auth/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password }),
            });

            const data = await response.json();

            if (response.ok && data.access_token) {
                setTokens(data.access_token, data.refresh_token || '');
                window.location.href = typeof NEXT_URL !== 'undefined' ? NEXT_URL : '/process/';
            } else {
                errorDiv.textContent = data.detail || 'Identifiants invalides';
                errorDiv.style.display = 'block';
            }
        } catch {
            errorDiv.textContent = 'Erreur de connexion au serveur';
            errorDiv.style.display = 'block';
        }
    });
}