/**
 * Chef AI Assistant — Authentication Module
 * Handles login, registration, token persistence, and auth guards.
 */

// ==============================================================================
// API Configuration
// ==============================================================================

const PRODUCTION_API_BASE = 'https://ai-chef-seven-snowy.vercel.app';

/**
 * Chef AI Assistant — Authentication Module
 */

async function resolveApiBase() {
  // إذا كان الشغل محلياً على الكمبيوتر
  if (
    window.location.protocol === 'file:' ||
    window.location.hostname === 'localhost' ||
    window.location.hostname === '127.0.0.1'
  ) {
    return 'http://127.0.0.1:8000';
  }
  // على Vercel: نرجع نص فارغ ليستخدم Relative Paths والتوجيه التلقائي عبر vercel.json
  return '';
}


// ==============================================================================
// Friendly Errors
// ==============================================================================

function friendlyFetchError(err) {
  if (err instanceof TypeError) {
    return 'Could not connect to the server. Please try again.';
  }

  return err.message;
}


// ==============================================================================
// Local Storage
// ==============================================================================

const TOKEN_KEY = 'chef_access_token';
const USER_KEY = 'chef_user_data';

function getStoredToken() {
  return localStorage.getItem(TOKEN_KEY);
}

function setStoredSession(token, user) {
  localStorage.setItem(TOKEN_KEY, token);

  if (user) {
    localStorage.setItem(
      USER_KEY,
      JSON.stringify(user)
    );
  }
}

function getStoredUser() {
  const userJson = localStorage.getItem(USER_KEY);

  try {
    return userJson
      ? JSON.parse(userJson)
      : null;
  } catch {
    return null;
  }
}

function clearStoredSession() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}


// ==============================================================================
// Logout
// ==============================================================================

function logout() {
  clearStoredSession();

  window.location.href = 'login.html';
}


// ==============================================================================
// Authentication Guards
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
// Register
// ==============================================================================

async function registerUser(username, email, password) {
  try {

    const apiBase = await resolveApiBase();

    const response = await fetch(
      `${apiBase}/auth/register`,
      {
        method: 'POST',

        headers: {
          'Content-Type': 'application/json'
        },

        body: JSON.stringify({
          username,
          email,
          password
        })
      }
    );


    const responseText = await response.text();

    let data = {};


    if (responseText) {
      try {

        data = JSON.parse(responseText);

      } catch {

        throw new Error(
          `Server returned an invalid response (${response.status}).`
        );

      }
    }


    if (!response.ok) {

      throw new Error(
        data.detail ||
        'Registration failed. Please check your details.'
      );

    }


    setStoredSession(
      data.access_token,
      data.user
    );


    return {
      success: true,
      data
    };


  } catch (err) {

    return {
      success: false,
      error: friendlyFetchError(err)
    };

  }
}


// ==============================================================================
// Login
// ==============================================================================

async function loginUser(login, password) {
  try {

    const apiBase = await resolveApiBase();


    const response = await fetch(
      `${apiBase}/auth/login`,
      {
        method: 'POST',

        headers: {
          'Content-Type': 'application/json'
        },

        body: JSON.stringify({
          login,
          password
        })
      }
    );


    const responseText = await response.text();

    let data = {};


    if (responseText) {

      try {

        data = JSON.parse(responseText);

      } catch {

        throw new Error(
          `Server returned an invalid response (${response.status}).`
        );

      }

    }


    if (!response.ok) {

      throw new Error(
        data.detail ||
        'Invalid email/username or password.'
      );

    }


    setStoredSession(
      data.access_token,
      data.user
    );


    return {
      success: true,
      data
    };


  } catch (err) {

    return {
      success: false,
      error: friendlyFetchError(err)
    };

  }
}


// ==============================================================================
// Authenticated Fetch
// ==============================================================================

async function authFetch(endpoint, options = {}) {
  const token = getStoredToken();

  if (!token) {
    window.location.href = 'login.html';
    throw new Error('Unauthorized');
  }

  const apiBase = await resolveApiBase();

  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
    'Authorization': `Bearer ${token}`
  };

  try {
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
  } catch (err) {
    console.error('AuthFetch error:', err);
    throw err;
  }
}