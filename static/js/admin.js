const statusLabels = {
    new: "Новая заявка",
    pending: "Ожидает",
    confirmed: "Подтверждена",
    cancelled: "Отменена",
    completed: "Завершена",
};

function formatDate(value) {
    return new Date(value).toLocaleDateString("ru-RU");
}

function formatDateTime(dateValue, timeValue) {
    return `${formatDate(dateValue)} ${timeValue}`;
}

function buildQuery() {
    const search = document.getElementById("search-input").value.trim();
    const date = document.getElementById("date-filter").value;
    const status = document.getElementById("status-filter").value;
    const params = new URLSearchParams();
    if (search) params.set("search", search);
    if (date) params.set("date", date);
    if (status) params.set("status", status);
    return params.toString();
}

async function fetchJson(url, options = {}) {
    const response = await fetch(url, options);
    const payload = await response.json().catch(() => null);
    if (!response.ok) {
        throw new Error(payload?.detail || "Ошибка запроса");
    }
    return payload;
}

function createStatusSelect(booking) {
    const select = document.createElement("select");
    select.className = "status-select";

    Object.entries(statusLabels).forEach(([value, label]) => {
        const option = document.createElement("option");
        option.value = value;
        option.textContent = label;
        option.selected = booking.status === value;
        select.appendChild(option);
    });

    select.addEventListener("change", async () => {
        await fetchJson(`/api/bookings/${booking.id}/status`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ status: select.value }),
        });
        await refreshAdminData();
    });

    return select;
}

function renderBookings(bookings) {
    const tbody = document.getElementById("bookings-body");
    tbody.innerHTML = "";

    if (!bookings.length) {
        tbody.innerHTML = '<tr><td colspan="5">Записей не найдено.</td></tr>';
        return;
    }

    bookings.forEach((booking) => {
        const row = document.createElement("tr");
        const deleteButton = document.createElement("button");
        deleteButton.className = "button button-secondary danger-button";
        deleteButton.type = "button";
        deleteButton.textContent = "Удалить";
        deleteButton.addEventListener("click", async () => {
            await fetch("/api/bookings/" + booking.id, { method: "DELETE" });
            await refreshAdminData();
        });

        row.innerHTML = `
            <td>
                <strong>${booking.client?.name || booking.user?.email || "Без имени"}</strong><br>
                <span>${booking.client?.phone || booking.client?.email || booking.user?.email || ""}</span>
            </td>
            <td>
                <strong>${booking.training_type}</strong><br>
                <span>${booking.trainer}</span>
            </td>
            <td>${formatDateTime(booking.date, booking.time)}</td>
            <td></td>
            <td></td>
        `;

        row.children[3].appendChild(createStatusSelect(booking));
        row.children[4].appendChild(deleteButton);
        tbody.appendChild(row);
    });
}

function renderClients(clients) {
    const container = document.getElementById("clients-list");
    container.innerHTML = clients.length
        ? clients.map((client) => `
            <article class="client-card">
                <div class="client-card-header">
                    <div>
                        <h3>${client.name}</h3>
                        <p>${client.phone || client.email || "Контакты не указаны"}</p>
                    </div>
                    <div class="client-card-meta">
                        <span>Записей: ${client.bookings.length}</span>
                        <span>Создан: ${formatDate(client.created_at)}</span>
                    </div>
                </div>
                <label>
                    <span>Заметка</span>
                    <textarea class="client-note" rows="3" data-client-id="${client.id}">${client.note || ""}</textarea>
                </label>
                <button class="button button-secondary save-client-note" data-client-id="${client.id}" type="button">Сохранить заметку</button>
                <div class="client-bookings">
                    ${client.bookings.length ? client.bookings.map((booking) => `
                        <div class="booking-history-item">
                            <strong>${booking.training_type}</strong>
                            <div>${booking.trainer}</div>
                            <div>${formatDateTime(booking.date, booking.time)}</div>
                            <div>${statusLabels[booking.status] || booking.status}</div>
                        </div>
                    `).join("") : "<p>История записей пока отсутствует.</p>"}
                </div>
            </article>
        `).join("")
        : "<p>Клиенты не найдены.</p>";

    document.querySelectorAll(".save-client-note").forEach((button) => {
        button.addEventListener("click", async () => {
            const clientId = button.dataset.clientId;
            const note = document.querySelector(`.client-note[data-client-id="${clientId}"]`).value;
            await fetchJson(`/api/clients/${clientId}/note`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ note }),
            });
            await refreshAdminData();
        });
    });
}

function renderUsers(users) {
    const container = document.getElementById("users-list");
    container.innerHTML = users.map((user) => `
        <article class="stack-card">
            <div class="stack-head">
                <strong>#${user.id} ${user.profile?.name || "Без имени"}</strong>
                <span class="pill">${user.role}</span>
            </div>
            <p>${user.phone || user.email || "Логин не указан"}</p>
            <div class="inline-form">
                <select class="admin-user-role" data-id="${user.id}">
                    <option value="client" ${user.role === "client" ? "selected" : ""}>client</option>
                    <option value="trainer" ${user.role === "trainer" ? "selected" : ""}>trainer</option>
                    <option value="admin" ${user.role === "admin" ? "selected" : ""}>admin</option>
                </select>
                <select class="admin-user-active" data-id="${user.id}">
                    <option value="true" ${user.is_active ? "selected" : ""}>active</option>
                    <option value="false" ${!user.is_active ? "selected" : ""}>disabled</option>
                </select>
                <button class="button button-secondary save-user" data-id="${user.id}" type="button">Сохранить</button>
            </div>
        </article>
    `).join("");

    document.querySelectorAll(".save-user").forEach((button) => {
        button.addEventListener("click", async () => {
            const id = button.dataset.id;
            const role = document.querySelector(`.admin-user-role[data-id="${id}"]`).value;
            const isActive = document.querySelector(`.admin-user-active[data-id="${id}"]`).value === "true";
            const name = users.find((item) => String(item.id) === String(id)).profile?.name || "Пользователь";
            await fetchJson(`/api/admin/users/${id}`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ role, is_active: isActive, name }),
            });
            await refreshAdminData();
        });
    });
}

function renderTrainers(trainers) {
    const container = document.getElementById("trainers-list");
    container.innerHTML = trainers.map((trainer) => `
        <article class="stack-card">
            <div class="stack-head">
                <strong>#${trainer.id} ${trainer.name}</strong>
                <span class="pill">${trainer.experience}</span>
            </div>
            <p>${trainer.specialization}</p>
            <p class="muted-text">${trainer.bio || ""}</p>
            <p class="muted-text">Связанный пользователь: ${trainer.user_id || "не указан"}</p>
        </article>
    `).join("");
}

function renderSubscriptions(subscriptions) {
    const container = document.getElementById("subscriptions-list");
    container.innerHTML = subscriptions.map((item) => `
        <article class="stack-card">
            <div class="stack-head">
                <strong>#${item.id} ${item.title}</strong>
                <span class="pill">${item.price} ₽</span>
            </div>
            <p>${item.description}</p>
            <p class="muted-text">Дней: ${item.duration_days} / Тренировок: ${item.total_sessions ?? "без лимита"}</p>
        </article>
    `).join("");
}

function renderUserSubscriptions(items) {
    const container = document.getElementById("user-subscriptions-list");
    container.innerHTML = items.map((item) => `
        <article class="stack-card">
            <div class="stack-head">
                <strong>${item.subscription.title}</strong>
                <span class="pill">${item.status}</span>
            </div>
            <p>Клиент: #${item.user_id} ${item.user?.profile?.name || item.user?.email || item.user?.phone || ""}</p>
            <p>До ${formatDate(item.end_date)}</p>
            <p class="muted-text">Остаток тренировок: ${item.remaining_sessions ?? "без лимита"}</p>
        </article>
    `).join("");
}

async function loadStats() {
    const stats = await fetchJson("/api/stats");
    document.getElementById("stat-total").textContent = stats.total_bookings;
    document.getElementById("stat-new").textContent = stats.new_bookings;
    document.getElementById("stat-pending").textContent = stats.pending_bookings;
    document.getElementById("stat-today").textContent = stats.today_bookings;
    document.getElementById("stat-completed").textContent = stats.completed_bookings;
    document.getElementById("stat-clients").textContent = stats.total_clients;
    document.getElementById("stat-users").textContent = stats.total_users;
    document.getElementById("stat-subscriptions").textContent = stats.active_subscriptions;
}

async function refreshAdminData() {
    const query = buildQuery();
    const searchValue = document.getElementById("search-input").value.trim();
    const bookingsUrl = query ? `/api/bookings?${query}` : "/api/bookings";
    const clientsUrl = searchValue ? `/api/clients?search=${encodeURIComponent(searchValue)}` : "/api/clients";

    const [bookings, clients, users, trainers, subscriptions, userSubscriptions] = await Promise.all([
        fetchJson(bookingsUrl),
        fetchJson(clientsUrl),
        fetchJson("/api/admin/users"),
        fetchJson("/api/admin/trainers"),
        fetchJson("/api/admin/subscriptions"),
        fetchJson("/api/admin/user-subscriptions"),
    ]);

    renderBookings(bookings);
    renderClients(clients);
    renderUsers(users);
    renderTrainers(trainers);
    renderSubscriptions(subscriptions);
    renderUserSubscriptions(userSubscriptions);
    await loadStats();
}

function setupFormHandlers() {
    document.getElementById("trainer-form").addEventListener("submit", async (event) => {
        event.preventDefault();
        const form = event.currentTarget;
        const message = document.getElementById("trainer-form-message");
        const data = Object.fromEntries(new FormData(form).entries());
        try {
            await fetchJson("/api/admin/trainers", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    ...data,
                    user_id: data.user_id ? Number(data.user_id) : null,
                }),
            });
            form.reset();
            message.textContent = "Тренер добавлен.";
            await refreshAdminData();
        } catch (error) {
            message.textContent = error.message;
        }
    });

    document.getElementById("subscription-form").addEventListener("submit", async (event) => {
        event.preventDefault();
        const form = event.currentTarget;
        const message = document.getElementById("subscription-form-message");
        const data = Object.fromEntries(new FormData(form).entries());
        try {
            await fetchJson("/api/admin/subscriptions", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    ...data,
                    price: Number(data.price),
                    duration_days: Number(data.duration_days),
                    total_sessions: data.total_sessions ? Number(data.total_sessions) : null,
                    is_active: true,
                }),
            });
            form.reset();
            message.textContent = "Абонемент добавлен.";
            await refreshAdminData();
        } catch (error) {
            message.textContent = error.message;
        }
    });

    document.getElementById("assign-form").addEventListener("submit", async (event) => {
        event.preventDefault();
        const form = event.currentTarget;
        const message = document.getElementById("assign-form-message");
        const data = Object.fromEntries(new FormData(form).entries());
        try {
            await fetchJson("/api/admin/subscriptions/assign", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    user_id: Number(data.user_id),
                    subscription_id: Number(data.subscription_id),
                    start_date: data.start_date,
                    remaining_sessions: data.remaining_sessions ? Number(data.remaining_sessions) : null,
                }),
            });
            form.reset();
            message.textContent = "Абонемент назначен.";
            await refreshAdminData();
        } catch (error) {
            message.textContent = error.message;
        }
    });
}

document.addEventListener("DOMContentLoaded", async () => {
    const controls = ["search-input", "date-filter", "status-filter"];
    controls.forEach((id) => {
        document.getElementById(id).addEventListener("input", refreshAdminData);
        document.getElementById(id).addEventListener("change", refreshAdminData);
    });
    document.getElementById("refresh-button").addEventListener("click", refreshAdminData);
    setupFormHandlers();
    document.querySelector('#assign-form input[name="start_date"]').value = new Date().toISOString().split("T")[0];
    await refreshAdminData();
});
