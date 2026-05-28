async function submitAuthForm(event, endpoint, messageId, redirectPath) {
    event.preventDefault();
    const form = event.currentTarget;
    const message = document.getElementById(messageId);
    const data = Object.fromEntries(new FormData(form).entries());

    if (data.phone === "") {
        delete data.phone;
    }
    if (data.email === "") {
        delete data.email;
    }

    try {
        const response = await fetch(endpoint, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data),
        });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) {
            throw new Error(payload.detail || "Ошибка авторизации");
        }
        window.location.href = payload.role === "admin" ? "/admin" : redirectPath;
    } catch (error) {
        message.textContent = error.message;
    }
}

document.addEventListener("DOMContentLoaded", () => {
    const loginForm = document.getElementById("login-form");
    const registerForm = document.getElementById("register-form");

    if (loginForm) {
        loginForm.addEventListener("submit", (event) => submitAuthForm(event, "/api/auth/login", "login-message", "/cabinet"));
    }
    if (registerForm) {
        registerForm.addEventListener("submit", (event) => submitAuthForm(event, "/api/auth/register", "register-message", "/cabinet"));
    }
});
