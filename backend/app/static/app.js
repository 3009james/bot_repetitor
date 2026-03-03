const tg = window.Telegram?.WebApp;

const state = {
  me: null,
  slots: [],
  adminSlots: [],
  adminBookings: [],
  selectedDay: null,
};

const DEFAULT_STUDENT_AVATAR =
  "data:image/svg+xml;charset=UTF-8,%3csvg xmlns='http://www.w3.org/2000/svg' width='128' height='128' viewBox='0 0 128 128'%3e%3crect width='128' height='128' rx='28' fill='%2313284c'/%3e%3ctext x='50%25' y='54%25' dominant-baseline='middle' text-anchor='middle' fill='%23edf4ff' font-family='Segoe UI' font-size='34'%3eTG%3c/text%3e%3c/svg%3e";
const DEFAULT_TUTOR_PHOTO =
  "data:image/svg+xml;charset=UTF-8,%3csvg xmlns='http://www.w3.org/2000/svg' width='640' height='640' viewBox='0 0 640 640'%3e%3crect width='640' height='640' rx='36' fill='%2313284c'/%3e%3ctext x='50%25' y='50%25' dominant-baseline='middle' text-anchor='middle' fill='%23edf4ff' font-family='Segoe UI' font-size='44'%3e%D0%A4%D0%BE%D1%82%D0%BE%3c/text%3e%3c/svg%3e";

const elements = {
  studentAvatar: document.getElementById("student-avatar"),
  greetingTitle: document.getElementById("greeting-title"),
  tutorName: document.getElementById("tutor-name"),
  aboutText: document.getElementById("about-text"),
  tutorPhoto: document.getElementById("tutor-photo"),
  roleBadge: document.getElementById("role-badge"),
  promoStatus: document.getElementById("promo-status"),
  inviteFriendButton: document.getElementById("invite-friend-button"),
  statusCard: document.getElementById("status-card"),
  daysRow: document.getElementById("days-row"),
  slotsGrid: document.getElementById("slots-grid"),
  emptyState: document.getElementById("empty-state"),
  adminPanel: document.getElementById("admin-panel"),
  profileForm: document.getElementById("profile-form"),
  photoForm: document.getElementById("photo-form"),
  slotForm: document.getElementById("slot-form"),
  profileName: document.getElementById("profile-name"),
  profileAbout: document.getElementById("profile-about"),
  photoFile: document.getElementById("profile-photo-file"),
  slotDatetime: document.getElementById("slot-datetime"),
  slotDuration: document.getElementById("slot-duration"),
  adminSlots: document.getElementById("admin-slots"),
  adminBookings: document.getElementById("admin-bookings"),
  refreshButton: document.getElementById("refresh-button"),
};

function initTelegram() {
  if (!tg) {
    return;
  }

  tg.ready();
  tg.expand();
  tg.setHeaderColor("#091224");
  tg.setBackgroundColor("#091224");
}

function getTelegramInitData() {
  if (tg?.initData) {
    return tg.initData;
  }

  const fromHash = new URLSearchParams(window.location.hash.replace(/^#/, "")).get("tgWebAppData");
  if (fromHash) {
    return fromHash;
  }

  const fromSearch = new URLSearchParams(window.location.search).get("tgWebAppData");
  if (fromSearch) {
    return fromSearch;
  }

  return "";
}

async function apiFetch(path, options = {}) {
  const headers = new Headers(options.headers || {});
  const initData = getTelegramInitData();
  if (initData) {
    headers.set("X-Telegram-Init-Data", initData);
  }

  const response = await fetch(path, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail || "Ошибка запроса");
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

function formatDate(dateString, options = {}) {
  return new Date(dateString).toLocaleString("ru-RU", options);
}

function toDayKey(dateString) {
  const date = new Date(dateString);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function notify(message) {
  if (tg?.showAlert) {
    tg.showAlert(message);
    return;
  }
  window.alert(message);
}

function confirmAction(message) {
  if (tg?.showConfirm) {
    return new Promise((resolve) => {
      tg.showConfirm(message, (confirmed) => resolve(Boolean(confirmed)));
    });
  }

  if (typeof window.confirm === "function") {
    return Promise.resolve(window.confirm(message));
  }

  return Promise.resolve(true);
}

function buildDayMap(slots) {
  return slots.reduce((acc, slot) => {
    const dayKey = toDayKey(slot.start_at);
    if (!acc[dayKey]) {
      acc[dayKey] = [];
    }
    acc[dayKey].push(slot);
    return acc;
  }, {});
}

function renderPromo() {
  const referral = state.me.referral;
  const statuses = [];

  if (referral.current_slot_discount_percent === 50) {
    statuses.push("У вас активна скидка 50% на следующую запись.");
  } else if (referral.current_slot_discount_percent === 20) {
    statuses.push("Для вас активна скидка 20% на первую запись по приглашению.");
  }

  if (referral.reward_count > 0) {
    statuses.push(`Доступно бонусов 50%: ${referral.reward_count}.`);
  }

  if (referral.link_copied) {
    statuses.push("Реферальная ссылка уже копировалась.");
  }

  elements.promoStatus.textContent =
    statuses.join(" ") || "Скопируйте ссылку и отправьте ее другу прямо из Telegram.";
}

function renderProfile() {
  const { user, profile, upcoming_bookings: upcomingBookings } = state.me;
  elements.greetingTitle.textContent = `Здравствуйте, ${user.first_name}`;
  elements.studentAvatar.src = user.photo_url || DEFAULT_STUDENT_AVATAR;
  elements.tutorName.textContent = profile.tutor_name;
  elements.aboutText.textContent = profile.about_text;
  elements.tutorPhoto.src = profile.tutor_photo_url || DEFAULT_TUTOR_PHOTO;
  elements.roleBadge.classList.toggle("hidden", !user.is_admin);

  renderPromo();

  if (upcomingBookings.length) {
    elements.statusCard.classList.remove("hidden");
    elements.statusCard.innerHTML = `
      <strong>Ваши ближайшие записи</strong>
      ${upcomingBookings
        .map(
          (booking) => `
            <div class="list-item">
              <div>
                <strong>${formatDate(booking.start_at, {
                  day: "2-digit",
                  month: "2-digit",
                  hour: "2-digit",
                  minute: "2-digit",
                })}</strong>
                <span>До ${formatDate(booking.end_at, { hour: "2-digit", minute: "2-digit" })}</span>
                ${
                  booking.discount_label
                    ? `<span class="discount-meta">${escapeHtml(booking.discount_label)}</span>`
                    : ""
                }
              </div>
              <button class="danger-button" data-cancel-own-booking="${booking.id}" type="button">Отменить</button>
            </div>
          `,
        )
        .join("")}
    `;
  } else {
    elements.statusCard.classList.add("hidden");
    elements.statusCard.innerHTML = "";
  }

  if (user.is_admin) {
    elements.adminPanel.classList.remove("hidden");
    elements.profileName.value = profile.tutor_name;
    elements.profileAbout.value = profile.about_text;
  }
}

function renderSlots() {
  const dayMap = buildDayMap(state.slots);
  const dayKeys = Object.keys(dayMap);

  if (!dayKeys.length) {
    elements.daysRow.innerHTML = "";
    elements.slotsGrid.innerHTML = "";
    elements.emptyState.classList.remove("hidden");
    elements.emptyState.textContent = "Свободных слотов пока нет.";
    return;
  }

  elements.emptyState.classList.add("hidden");
  state.selectedDay = dayKeys.includes(state.selectedDay) ? state.selectedDay : dayKeys[0];

  elements.daysRow.innerHTML = dayKeys
    .map((dayKey) => {
      const date = new Date(dayKey);
      const label = date.toLocaleDateString("ru-RU", {
        weekday: "short",
        day: "2-digit",
        month: "2-digit",
      });
      const isActive = state.selectedDay === dayKey ? "active" : "";
      return `<button class="day-pill ${isActive}" data-day="${dayKey}" type="button">${label}</button>`;
    })
    .join("");

  elements.slotsGrid.innerHTML = dayMap[state.selectedDay]
    .map((slot) => {
      const start = formatDate(slot.start_at, { hour: "2-digit", minute: "2-digit" });
      const end = formatDate(slot.end_at, { hour: "2-digit", minute: "2-digit" });
      const discountBadge =
        slot.discount_percent > 0
          ? `<span class="slot-discount-badge">Скидка ${slot.discount_percent}%</span>`
          : "";
      return `
        <button class="slot-button" data-slot-id="${slot.id}" type="button">
          <strong>${start} - ${end}</strong>
          <span>Записаться</span>
          ${discountBadge}
        </button>
      `;
    })
    .join("");
}

function renderAdminSlots() {
  elements.adminSlots.innerHTML = state.adminSlots.length
    ? state.adminSlots
        .map(
          (slot) => `
            <div class="list-item">
              <div>
                <strong>${formatDate(slot.start_at, {
                  day: "2-digit",
                  month: "2-digit",
                  hour: "2-digit",
                  minute: "2-digit",
                })}</strong>
                <span>${formatDate(slot.end_at, { hour: "2-digit", minute: "2-digit" })}</span>
              </div>
              <button class="danger-button" data-delete-slot="${slot.id}" type="button">Удалить</button>
            </div>
          `,
        )
        .join("")
    : "<p>Свободных слотов пока нет.</p>";
}

function renderAdminBookings() {
  elements.adminBookings.innerHTML = state.adminBookings.length
    ? state.adminBookings
        .map((booking) => {
          const username = booking.username ? ` (@${escapeHtml(booking.username)})` : "";
          const discountMeta =
            booking.discount_percent > 0
              ? `<span class="discount-meta">Скидка ${booking.discount_percent}%</span>`
              : "";
          return `
            <div class="list-item">
              <div>
                <strong>${escapeHtml(booking.user_first_name)}${username}</strong>
                <span>${formatDate(booking.start_at, {
                  day: "2-digit",
                  month: "2-digit",
                  hour: "2-digit",
                  minute: "2-digit",
                })} - ${formatDate(booking.end_at, { hour: "2-digit", minute: "2-digit" })}</span>
                ${discountMeta}
              </div>
              <div>
                <span>ID: ${booking.user_telegram_id}</span>
                <button class="danger-button" data-cancel-booking="${booking.id}" type="button">Отменить</button>
              </div>
            </div>
          `;
        })
        .join("")
    : "<p>Записей пока нет.</p>";
}

async function loadMe() {
  state.me = await apiFetch("/api/me");
  renderProfile();
}

async function loadSlots() {
  state.slots = await apiFetch("/api/slots");
  renderSlots();
}

async function loadAdminData() {
  if (!state.me?.user?.is_admin) {
    return;
  }

  const [slots, bookings] = await Promise.all([
    apiFetch("/api/admin/slots"),
    apiFetch("/api/admin/bookings"),
  ]);
  state.adminSlots = slots;
  state.adminBookings = bookings;
  renderAdminSlots();
  renderAdminBookings();
}

async function refreshAll() {
  await loadMe();
  await loadSlots();
  await loadAdminData();
}

async function createBooking(slotId) {
  await apiFetch(`/api/bookings/${slotId}`, { method: "POST" });
  notify("Запись подтверждена.");
  await refreshAll();
}

async function cancelMyBooking(bookingId) {
  await apiFetch(`/api/bookings/${bookingId}`, { method: "DELETE" });
  notify("Запись отменена.");
  await refreshAll();
}

async function cancelBookingAsAdmin(bookingId) {
  await apiFetch(`/api/admin/bookings/${bookingId}`, { method: "DELETE" });
  notify("Запись отменена администратором.");
  await refreshAll();
}

async function saveProfile(event) {
  event.preventDefault();
  await apiFetch("/api/admin/profile", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      tutor_name: elements.profileName.value.trim(),
      about_text: elements.profileAbout.value.trim(),
    }),
  });
  await refreshAll();
}

async function uploadPhoto(event) {
  event.preventDefault();
  const file = elements.photoFile.files[0];
  if (!file) {
    return;
  }

  const formData = new FormData();
  formData.append("photo", file);
  await apiFetch("/api/admin/profile/photo", {
    method: "POST",
    body: formData,
  });
  elements.photoForm.reset();
  await refreshAll();
}

async function createSlot(event) {
  event.preventDefault();
  await apiFetch("/api/admin/slots", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      start_at: new Date(elements.slotDatetime.value).toISOString(),
      duration_minutes: Number(elements.slotDuration.value),
    }),
  });
  elements.slotForm.reset();
  elements.slotDuration.value = "60";
  await refreshAll();
}

async function deleteSlot(slotId) {
  await apiFetch(`/api/admin/slots/${slotId}`, { method: "DELETE" });
  await refreshAll();
}

async function inviteFriend() {
  const referral = await apiFetch("/api/referrals/copy", { method: "POST" });
  state.me.referral = referral;
  renderPromo();

  if (!referral.referral_link) {
    notify("Ссылка на бота пока недоступна.");
    return;
  }

  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(referral.referral_link);
    notify("Ссылка приглашения скопирована.");
    return;
  }

  notify(`Скопируйте ссылку вручную: ${referral.referral_link}`);
}

document.addEventListener("click", async (event) => {
  const dayButton = event.target.closest("[data-day]");
  if (dayButton) {
    state.selectedDay = dayButton.dataset.day;
    renderSlots();
    return;
  }

  const slotButton = event.target.closest("[data-slot-id]");
  if (slotButton) {
    const slot = state.slots.find((item) => String(item.id) === String(slotButton.dataset.slotId));
    const slotLabel = slot
      ? `${formatDate(slot.start_at, {
          day: "2-digit",
          month: "2-digit",
          hour: "2-digit",
          minute: "2-digit",
        })} - ${formatDate(slot.end_at, { hour: "2-digit", minute: "2-digit" })}`
      : "выбранное время";
    if (!(await confirmAction(`Подтвердите запись на ${slotLabel}?`))) {
      return;
    }
    try {
      await createBooking(slotButton.dataset.slotId);
    } catch (error) {
      notify(error.message);
    }
    return;
  }

  const deleteButton = event.target.closest("[data-delete-slot]");
  if (deleteButton) {
    try {
      await deleteSlot(deleteButton.dataset.deleteSlot);
    } catch (error) {
      notify(error.message);
    }
    return;
  }

  const ownCancelButton = event.target.closest("[data-cancel-own-booking]");
  if (ownCancelButton) {
    if (!(await confirmAction("Отменить вашу запись?"))) {
      return;
    }
    try {
      await cancelMyBooking(ownCancelButton.dataset.cancelOwnBooking);
    } catch (error) {
      notify(error.message);
    }
    return;
  }

  const adminCancelButton = event.target.closest("[data-cancel-booking]");
  if (adminCancelButton) {
    if (!(await confirmAction("Отменить запись ученика?"))) {
      return;
    }
    try {
      await cancelBookingAsAdmin(adminCancelButton.dataset.cancelBooking);
    } catch (error) {
      notify(error.message);
    }
  }
});

elements.profileForm.addEventListener("submit", async (event) => {
  try {
    await saveProfile(event);
  } catch (error) {
    notify(error.message);
  }
});

elements.photoForm.addEventListener("submit", async (event) => {
  try {
    await uploadPhoto(event);
  } catch (error) {
    notify(error.message);
  }
});

elements.slotForm.addEventListener("submit", async (event) => {
  try {
    await createSlot(event);
  } catch (error) {
    notify(error.message);
  }
});

elements.refreshButton.addEventListener("click", async () => {
  try {
    await refreshAll();
  } catch (error) {
    notify(error.message);
  }
});

elements.inviteFriendButton.addEventListener("click", async () => {
  try {
    await inviteFriend();
  } catch (error) {
    notify(error.message);
  }
});

async function bootstrap() {
  initTelegram();
  try {
    await refreshAll();
  } catch (error) {
    console.error(error);
    const message = error.message || "Не удалось загрузить приложение";
    notify(message);
    elements.emptyState.classList.remove("hidden");
    elements.emptyState.textContent = message;
  }
}

bootstrap();
