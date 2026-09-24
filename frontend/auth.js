/**
 * Chef AI Assistant — Authentication Module
 * Handles login, registration, token persistence, and auth guards.
 */

// Prefer the current origin when the app is served from the backend.
// When opened directly as a file (double-clicked HTML), the backend could be
// running on either port 8000 (the README's default) or 8001 (run_server.bat),
// so we auto-detect which one is actually alive instead of hardcoding a guess —
// that mismatch was the cause of the "Failed to fetch" error on Create Account.
const CANDIDATE_PORTS = [8000, 8001];
const LOCAL_HOSTNAMES = ['localhost', '127.0.0.1'];
let cachedApiBase = null;

async function resolveApiBase() {
  if (cachedApiBase) return cachedApiBase;

  if (window.location.protocol !== 'file:') {
    const currentPort = window.location.port;
    const isKnownBackendPort = CANDIDATE_PORTS.includes(Number(currentPort));
    const isLocalFrontend =
      LOCAL_HOSTNAMES.includes(window.location.hostname) &&
      !isKnownBackendPort;

    // Live Server serves the frontend on ports such as 5500; the API still
    // runs on the FastAPI port and must be discovered separately.
    if (isKnownBackendPort) {
      cachedApiBase = window.location.origin;
      return cachedApiBase;
    }

    if (!isLocalFrontend) {
      cachedApiBase = window.location.origin;
      return cachedApiBase;
    }
  }

  for (const port of CANDIDATE_PORTS) {
    const base = `http://127.0.0.1:${port}`;
    let timeoutId;
    try {
      const controller = new AbortController();
      timeoutId = setTimeout(() => controller.abort(), 1000);
      const res = await fetch(`${base}/health`, { signal: controller.signal });
      if (res.ok) {
        cachedApiBase = base;
        return cachedApiBase;
      }
    } catch (_) {
      // This port isn't responding — try the next candidate.
    } finally {
      clearTimeout(timeoutId);
    }
  }

  // Nothing responded; default to 8000 so any resulting error is at least consistent.
  cachedApiBase = 'http://127.0.0.1:8000';
  return cachedApiBase;
}

function friendlyFetchError(err) {
  if (err instanceof TypeError) {
    return 'Could not connect to the server. Make sure the backend is running (double-click run_server.bat), then try again.';
  }
  return err.message;
}

const TOKEN_KEY = 'chef_access_token';
const USER_KEY = 'chef_user_data';

// ==============================================================================
// Token & Session Storage
// ==============================================================================

function getStoredToken() {
  return localStorage.getItem(TOKEN_KEY);
}

function setStoredSession(token, user) {
  localStorage.setItem(TOKEN_KEY, token);
  if (user) {
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  }
}

function getStoredUser() {
  const userJson = localStorage.getItem(USER_KEY);
  try {
    return userJson ? JSON.parse(userJson) : null;
  } catch {
    return null;
  }
}

function clearStoredSession() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

function logout() {
  clearStoredSession();
  window.location.href = 'login.html';
}

// ==============================================================================
// Auth Guard
// ==============================================================================

function requireAuthentication() {
  const token = getStoredToken();
  if (!token) {
    window.location.href = 'login.html';
    return false;
  }
  return true;
}

function redirectIfAuthenticated() {
  const token = getStoredToken();
  if (token) {
    window.location.href = 'index.html';
  }
}

// ==============================================================================
// API Calls: Register & Login
// ==============================================================================

async function registerUser(username, email, password) {
  try {
    const apiBase = await resolveApiBase();
    const response = await fetch(`${apiBase}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, email, password })
    });

    const responseText = await response.text();
    let data = {};
    if (responseText) {
      try {
        data = JSON.parse(responseText);
      } catch {
        throw new Error(`Server returned an invalid response (${response.status}).`);
      }
    }
    if (!response.ok) {
      throw new Error(data.detail || 'Registration failed. Please check your details.');
    }

    setStoredSession(data.access_token, data.user);
    return { success: true, data };
  } catch (err) {
    return { success: false, error: friendlyFetchError(err) };
  }
}

async function loginUser(login, password) {
  try {
    const apiBase = await resolveApiBase();
    const response = await fetch(`${apiBase}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ login, password })
    });

    const responseText = await response.text();
    let data = {};
    if (responseText) {
      try {
        data = JSON.parse(responseText);
      } catch {
        throw new Error(`Server returned an invalid response (${response.status}).`);
      }
    }
    if (!response.ok) {
      throw new Error(data.detail || 'Invalid email/username or password.');
    }

    setStoredSession(data.access_token, data.user);
    return { success: true, data };
  } catch (err) {
    return { success: false, error: friendlyFetchError(err) };
  }
}

// Helper: Authenticated fetch wrapper
async function authFetch(endpoint, options = {}) {
  const token = getStoredToken();
  if (!token) {
    window.location.href = 'login.html';
    throw new Error('Unauthorized');
  }

const apiBase = 'https://ai-chef-seven-snowy.vercel.app';  const headers = {
    ...options.headers,
    'Authorization': `Bearer ${token}`
  };

  const response = await fetch(`${apiBase}${endpoint}`, {
    ...options,
    headers
  });

  if (response.status === 401) {
    clearStoredSession();
    window.location.href = 'login.html';
    throw new Error('Session expired. Please log in again.');
  }

  return response;
}
