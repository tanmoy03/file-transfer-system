(() => {
  const BACKEND_BASE = "http://172.20.10.2:8000";
  const TOKEN_KEY = "fs_token";
  const USER_KEY = "fs_user";

  const $ = (sel) => document.querySelector(sel);

  const backendUrlLabel = $("#backendUrlLabel");
  const loginForm = $("#loginForm");
  const registerForm = $("#registerForm");
  const loginUsername = $("#loginUsername");
  const loginPassword = $("#loginPassword");
  const registerUsername = $("#registerUsername");
  const registerPassword = $("#registerPassword");
  const toastsEl = $("#toasts");

  backendUrlLabel.textContent = BACKEND_BASE;

  function toast(type, text, ttlMs = 2600) {
    const el = document.createElement("div");
    el.className = `toast ${type}`;
    el.innerHTML = `
      <div class="msg">${escapeHtml(text)}</div>
      <button class="x" title="Dismiss">×</button>
    `;
    el.querySelector(".x").addEventListener("click", () => el.remove());
    toastsEl.prepend(el);
    if (ttlMs > 0) setTimeout(() => el.remove(), ttlMs);
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, (c) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    }[c]));
  }

  function saveAuth(token, username) {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(USER_KEY, username);
  }

  function hasAuth() {
    const token = localStorage.getItem(TOKEN_KEY) || "";
    const user = localStorage.getItem(USER_KEY) || "";
    return token.trim().length > 0 && user.trim().length > 0;
  }

  async function handleLoginSubmit(e) {
    e.preventDefault();

    const username = loginUsername.value.trim();
    const password = loginPassword.value.trim();

    if (!username || !password) {
      toast("error", "Username and password are required.");
      return;
    }

    try {
      const res = await fetch(`${BACKEND_BASE}/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });

      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        toast("error", data.error || "Login failed");
        return;
      }

      saveAuth(data.token, data.username || username);
      toast("ok", `Logged in as ${data.username || username}`);
      setTimeout(() => {
        window.location.href = "./index.html";
      }, 400);
    } catch (err) {
      toast("error", `Login error: ${err}`);
    }
  }

  async function handleRegisterSubmit(e) {
    e.preventDefault();

    const username = registerUsername.value.trim();
    const password = registerPassword.value.trim();

    if (!username || !password) {
      toast("error", "Username and password are required.");
      return;
    }

    try {
      const res = await fetch(`${BACKEND_BASE}/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });

      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        toast("error", data.error || "Registration failed");
        return;
      }

      toast("ok", "Registration successful. You can now log in.");
      registerForm.reset();
    } catch (err) {
      toast("error", `Registration error: ${err}`);
    }
  }

  // If already logged in, skip auth page
  if (hasAuth()) {
    window.location.href = "./index.html";
  }

  loginForm.addEventListener("submit", handleLoginSubmit);
  registerForm.addEventListener("submit", handleRegisterSubmit);
})();