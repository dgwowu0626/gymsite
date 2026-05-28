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

function bookingCard(booking, canCancel = false) {
    return `
        <article class="stack-card">
            <div class="stack-head">
                <strong>${booking.training_type}</strong>
                <span class="pill">${statusLabels[booking.status] || booking.status}</span>
            </div>
            <p>${booking.trainer || "Без тренера"}</p>
            <p>${formatDate(booking.date)} ${booking.time}</p>
            ${booking.comment ? `<p class="muted-text">Комментарий: ${booking.comment}</p>` : ""}
            ${booking.trainer_comment ? `<p class="muted-text">Комментарий тренера: ${booking.trainer_comment}</p>` : ""}
            ${canCancel ? `<button class="button button-secondary cancel-booking" data-id="${booking.id}" type="button">Отменить запись</button>` : ""}
        </article>
    `;
}

async function fetchJson(url, options = {}) {
    const response = await fetch(url, options);
    const payload = await response.json().catch(() => null);
    if (!response.ok) {
        throw new Error(payload?.detail || "Ошибка запроса");
    }
    return payload;
}

async function loadTrainersSelect() {
    const select = document.querySelector('#booking-form select[name="trainer"]');
    if (!select) {
        return;
    }
    const trainers = await fetchJson("/api/trainers");
    select.innerHTML = [
        '<option value="">Не выбирать тренера</option>',
        ...trainers.map((trainer) => `<option value="${trainer.id}" data-trainer-name="${trainer.name}">${trainer.name}</option>`),
    ].join("");
}

function attachCancelActions() {
    document.querySelectorAll(".cancel-booking").forEach((button) => {
        button.addEventListener("click", async () => {
            await fetchJson(`/api/me/bookings/${button.dataset.id}/cancel`, { method: "PATCH" });
            await loadClientDashboard();
        });
    });
}

async function loadClientDashboard() {
    const data = await fetchJson("/api/me/dashboard");

    document.getElementById("client-profile").innerHTML = `
        <article class="stack-card">
            <strong>${data.user.profile?.name || "Пользователь"}</strong>
            <p>${data.user.phone || "Телефон не указан"}</p>
            <p>${data.user.email || "Email не указан"}</p>
        </article>
    `;

    const subscriptions = document.getElementById("client-subscriptions");
    subscriptions.innerHTML = data.active_subscriptions.length
        ? data.active_subscriptions.map((item) => `
            <article class="stack-card">
                <div class="stack-head">
                    <strong>${item.subscription.title}</strong>
                    <span class="pill">${item.status}</span>
                </div>
                <p>До ${formatDate(item.end_date)}</p>
                <p>Осталось тренировок: ${item.remaining_sessions ?? "без лимита"}</p>
            </article>
        `).join("")
        : "<p>Абонементы пока не назначены.</p>";

    const trainingTypeSelect = document.querySelector('#booking-form select[name="training_type"]');
    if (trainingTypeSelect) {
        const availableTitles = new Set(["Разовый визит"]);
        data.active_subscriptions.forEach((item) => {
            availableTitles.add(item.subscription.title);
            if (item.subscription.title === "Месячный абонемент") {
                availableTitles.add("Персональные тренировки");
                availableTitles.add("Групповые занятия");
            }
        });
        Array.from(trainingTypeSelect.options).forEach((option) => {
            option.disabled = !availableTitles.has(option.value);
        });
        if (trainingTypeSelect.selectedOptions[0]?.disabled) {
            trainingTypeSelect.value = "Разовый визит";
        }
    }

    document.getElementById("client-upcoming").innerHTML = data.upcoming_bookings.length
        ? data.upcoming_bookings.map((booking) => bookingCard(booking, true)).join("")
        : "<p>Активных записей пока нет.</p>";

    document.getElementById("client-history").innerHTML = data.history.length
        ? data.history.map((booking) => bookingCard(booking)).join("")
        : "<p>История тренировок пока пуста.</p>";

    attachCancelActions();
}

function trainerScheduleCard(booking) {
    return `
        <article class="stack-card">
            <div class="stack-head">
                <strong>${booking.client?.name || booking.user?.email || "Клиент"}</strong>
                <span class="pill">${statusLabels[booking.status] || booking.status}</span>
            </div>
            <p>${booking.training_type}</p>
            <p>${booking.trainer || "Без тренера"}</p>
            <p>${formatDate(booking.date)} ${booking.time}</p>
            <p class="muted-text">${booking.client?.phone || booking.user?.email || ""}</p>
            ${booking.status !== "completed" ? `
                <textarea class="trainer-complete-comment" rows="3" placeholder="Комментарий после тренировки"></textarea>
                <button class="button button-primary trainer-complete-button" data-id="${booking.id}" type="button">Отметить завершённой</button>
            ` : (booking.trainer_comment ? `<p class="muted-text">Комментарий: ${booking.trainer_comment}</p>` : "")}
        </article>
    `;
}

function attachCompleteActions() {
    document.querySelectorAll(".trainer-complete-button").forEach((button) => {
        button.addEventListener("click", async () => {
            const comment = button.parentElement.querySelector(".trainer-complete-comment")?.value || "";
            await fetchJson(`/api/trainer/bookings/${button.dataset.id}/complete`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ comment }),
            });
            await loadTrainerDashboard();
        });
    });
}

async function loadTrainerDashboard() {
    const data = await fetchJson("/api/trainer/dashboard");

    document.getElementById("trainer-profile").innerHTML = `
        <article class="stack-card">
            <strong>${data.trainer.name}</strong>
            <p>${data.trainer.specialization}</p>
            <p>${data.trainer.experience}</p>
            <p class="muted-text">${data.trainer.bio || ""}</p>
        </article>
    `;

    document.getElementById("trainer-day").innerHTML = data.day_schedule.length
        ? data.day_schedule.map(trainerScheduleCard).join("")
        : "<p>На сегодня записей нет.</p>";

    document.getElementById("trainer-week").innerHTML = data.week_schedule.length
        ? data.week_schedule.map(trainerScheduleCard).join("")
        : "<p>На ближайшую неделю записей нет.</p>";

    document.getElementById("trainer-clients").innerHTML = data.clients.length
        ? data.clients.map((client) => `
            <article class="stack-card">
                <strong>${client.name}</strong>
                <p>${client.phone || client.email || "Контакты не указаны"}</p>
                <p class="muted-text">${client.note || "Без заметки"}</p>
            </article>
        `).join("")
        : "<p>Клиентов пока нет.</p>";

    document.getElementById("trainer-history").innerHTML = data.workout_history.length
        ? data.workout_history.map((item) => `
            <article class="stack-card">
                <strong>Тренировка #${item.booking_id}</strong>
                <p>${formatDate(item.completed_at)}</p>
                <p class="muted-text">${item.notes || "Без комментария"}</p>
            </article>
        `).join("")
        : "<p>История завершённых тренировок пока пуста.</p>";

    attachCompleteActions();
}

document.addEventListener("DOMContentLoaded", async () => {
    const root = document.getElementById("account-app");
    if (!root) {
        return;
    }

    const role = root.dataset.role;
    if (role === "client") {
        await loadTrainersSelect();
        const form = document.getElementById("booking-form");
        form.querySelector('input[name="date"]').value = new Date().toISOString().split("T")[0];
        form.querySelector('input[name="date"]').min = new Date().toISOString().split("T")[0];
        await loadClientDashboard();
        return;
    }

    if (role === "trainer") {
        await loadTrainerDashboard();
    }
});

window.loadClientDashboard = loadClientDashboard;
