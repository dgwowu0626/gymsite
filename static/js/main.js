function applyBookingQueryDefaults() {
    const form = document.getElementById("booking-form");
    if (!form) {
        return;
    }

    const params = new URLSearchParams(window.location.search);
    const trainer = params.get("trainer");
    const trainingType = params.get("training_type");
    const today = new Date().toISOString().split("T")[0];

    const dateInput = form.querySelector('input[name="date"]');
    if (dateInput) {
        if (!dateInput.value) {
            dateInput.value = today;
        }
        dateInput.min = today;
    }

    const trainerField = form.querySelector('select[name="trainer"]');
    const trainingField = form.querySelector('select[name="training_type"]');
    if (trainer && trainerField) {
        const option = Array.from(trainerField.options).find((item) => item.dataset.trainerName === trainer);
        if (option) {
            trainerField.value = option.value;
        }
    }
    if (trainingType && trainingField) {
        trainingField.value = trainingType;
    }
}

function getBookingFormPayload(form) {
    const data = Object.fromEntries(new FormData(form).entries());
    const trainerSelect = form.querySelector('select[name="trainer"]');
    const trainerOption = trainerSelect?.selectedOptions?.[0];
    const trainerId = data.trainer ? Number(data.trainer) : null;
    const trainerName = trainerOption?.dataset?.trainerName || "";

    return {
        data,
        trainerId,
        trainerName,
    };
}

async function handleBookingSubmit(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const message = document.getElementById("booking-message");
    const mode = form.dataset.mode || "public";
    const { data, trainerId, trainerName } = getBookingFormPayload(form);

    try {
        const request =
            mode === "client"
                ? fetch("/api/me/bookings", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        trainer_id: trainerId,
                        date: data.date,
                        time: data.time,
                        training_type: data.training_type,
                        comment: data.comment || "",
                    }),
                })
                : fetch("/api/bookings", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        ...data,
                        trainer: trainerName || null,
                        trainer_id: trainerId,
                    }),
                });

        const response = await request;

        const payload = await response.json().catch(() => ({}));
        if (!response.ok) {
            throw new Error(payload.detail || "Не удалось сохранить заявку");
        }

        form.reset();
        applyBookingQueryDefaults();
        message.textContent =
            mode === "client"
                ? "Запись создана в личном кабинете."
                : "Заявка отправлена. Администратор увидит её в CRM.";

        if (mode === "client" && window.loadClientDashboard) {
            await window.loadClientDashboard();
        }
    } catch (error) {
        message.textContent = error.message;
    }
}

async function purchaseSubscription(subscriptionId, messageElement) {
    try {
        const response = await fetch(`/api/me/subscriptions/${subscriptionId}/purchase`, {
            method: "POST",
        });
        const payload = await response.json().catch(() => ({}));
        if (response.status === 401) {
            window.location.href = "/login";
            return;
        }
        if (response.status === 403) {
            throw new Error("Покупка доступна только клиентскому аккаунту");
        }
        if (!response.ok) {
            throw new Error(payload.detail || "Не удалось оформить абонемент");
        }
        messageElement.textContent = "Абонемент куплен. Посещения начислены в личный кабинет.";
    } catch (error) {
        messageElement.textContent = error.message;
    }
}

function initMembershipButtons() {
    const page = document.getElementById("memberships-page");
    if (!page) {
        return;
    }

    const message = document.getElementById("membership-message");
    page.querySelectorAll(".buy-subscription-button").forEach((button) => {
        button.addEventListener("click", async () => {
            await purchaseSubscription(button.dataset.subscriptionId, message);
        });
    });
}

document.addEventListener("DOMContentLoaded", () => {
    applyBookingQueryDefaults();
    const form = document.getElementById("booking-form");
    if (form) {
        form.addEventListener("submit", handleBookingSubmit);
    }
    initMembershipButtons();
});
