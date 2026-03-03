const tg = window.Telegram?.WebApp;

const state = {
  me: null,
  slots: [],
  adminSlots: [],
  adminBookings: [],
  students: [],
  selectedDay: null,
  daysDrag: {
    active: false,
    startX: 0,
    startScrollLeft: 0,
  },
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
  openPortfolioButton: document.getElementById("open-portfolio-button"),
  roleBadge: document.getElementById("role-badge"),
  promoStatus: document.getElementById("promo-status"),
  inviteFriendButton: document.getElementById("invite-friend-button"),
  statusCard: document.getElementById("status-card"),
  daysRow: document.getElementById("days-row"),
  daysScrollLeft: document.getElementById("days-scroll-left"),
  daysScrollRight: document.getElementById("days-scroll-right"),
  slotsGrid: document.getElementById("slots-grid"),
  emptyState: document.getElementById("empty-state"),
  adminPanel: document.getElementById("admin-panel"),
  profileForm: document.getElementById("profile-form"),
  photoForm: document.getElementById("photo-form"),
  slotForm: document.getElementById("slot-form"),
  portfolioForm: document.getElementById("portfolio-form"),
  portfolioArticlesPhotoForm: document.getElementById("portfolio-articles-photo-form"),
  portfolioProgramsPhotoForm: document.getElementById("portfolio-programs-photo-form"),
  portfolioEventsPhotoForm: document.getElementById("portfolio-events-photo-form"),
  profileName: document.getElementById("profile-name"),
  profileAbout: document.getElementById("profile-about"),
  photoFile: document.getElementById("profile-photo-file"),
  slotDatetime: document.getElementById("slot-datetime"),
  slotDuration: document.getElementById("slot-duration"),
  portfolioArticlesText: document.getElementById("portfolio-articles-text"),
  portfolioProgramsText: document.getElementById("portfolio-programs-text"),
  portfolioEventsText: document.getElementById("portfolio-events-text"),
  portfolioArticlesPhotoFile: document.getElementById("portfolio-articles-photo-file"),
  portfolioProgramsPhotoFile: document.getElementById("portfolio-programs-photo-file"),
  portfolioEventsPhotoFile: document.getElementById("portfolio-events-photo-file"),
  portfolioModal: document.getElementById("portfolio-modal"),
  closePortfolioButton: document.getElementById("close-portfolio-button"),
  portfolioList: document.getElementById("portfolio-list"),
  adminSlots: document.getElementById("admin-slots"),
  adminBookings: document.getElementById("admin-bookings"),
  refreshButton: document.getElementById("refresh-button"),
  toggleStudentsButton: document.getElementById("toggle-students-button"),
  studentsPanel: document.getElementById("students-panel"),
  studentsList: document.getElementById("students-list"),
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

  const response = await fetch(path, { ...options, headers });
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
    return new Promise((resolve) => tg.showConfirm(message, (confirmed) => resolve(Boolean(confirmed))));
  }
  return Promise.resolve(window.confirm(message));
}

function normalizeMeResponse(payload) {
  return {
    user: payload?.user || {
      telegram_id: 0,
      first_name: "Ученик",
      username: null,
      photo_url: null,
      is_admin: false,
    },
    profile: payload?.profile || {
      tutor_name: "Ваш репетитор",
      about_text: "",
      tutor_photo_url: null,
      portfolio_sections: [],
    },
    upcoming_bookings: Array.isArray(payload?.upcoming_bookings) ? payload.upcoming_bookings : [],
    referral: payload?.referral || {
      referral_link: null,
      link_copied: false,
      friend_discount_percent: 20,
      owner_discount_percent: 50,
      current_slot_discount_percent: 0,
      reward_count: 0,
      referred_discount_available: false,
    },
  };
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

function setupDaysDesktopScroll() {
  const row = elements.daysRow;
  if (!row || row.dataset.desktopScrollReady === "true") {
    return;
  }

  row.dataset.desktopScrollReady = "true";

  row.addEventListener(
    "wheel",
    (event) => {
      row.scrollLeft += event.deltaY || event.deltaX;
      event.preventDefault();
    },
    { passive: false },
  );

  row.addEventListener("mousedown", (event) => {
    if (event.target.closest(".day-pill")) {
      return;
    }
    state.daysDrag.active = true;
    state.daysDrag.startX = event.clientX;
    state.daysDrag.startScrollLeft = row.scrollLeft;
    row.classList.add("dragging");
  });

  window.addEventListener("mousemove", (event) => {
    if (!state.daysDrag.active) {
      return;
    }
    row.scrollLeft = state.daysDrag.startScrollLeft - (event.clientX - state.daysDrag.startX);
  });

  const stopDragging = () => {
    state.daysDrag.active = false;
    row.classList.remove("dragging");
  };

  window.addEventListener("mouseup", stopDragging);
  row.addEventListener("mouseleave", stopDragging);
}

function scrollDays(direction) {
  elements.daysRow?.scrollBy({ left: direction * 220, behavior: "smooth" });
}

function getPortfolioSection(index) {
  return state.me?.profile?.portfolio_sections?.[index] || { title: "", text: "", photo_url: null };
}

function renderPortfolioModal() {
  if (!elements.portfolioList) {
    return;
  }
  const sections = state.me?.profile?.portfolio_sections || [];
  elements.portfolioList.innerHTML = sections
    .map(
      (section) => `
        <article class="portfolio-item">
          <h4>${escapeHtml(section.title)}</h4>
          <p>${escapeHtml(section.text)}</p>
          <img class="portfolio-photo" src="${section.photo_url || DEFAULT_TUTOR_PHOTO}" alt="${escapeHtml(section.title)}" />
        </article>
      `,
    )
    .join("");
}

function openPortfolioModal() {
  if (!elements.portfolioModal) {
    return;
  }
  renderPortfolioModal();
  elements.portfolioModal?.classList.remove("hidden");
}

function closePortfolioModal() {
  elements.portfolioModal?.classList.add("hidden");
}

function renderPromo() {
  if (!elements.promoStatus) {
    return;
  }

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
                ${booking.discount_label ? `<span class="discount-meta">${escapeHtml(booking.discount_label)}</span>` : ""}
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
    if (elements.profileName) {
      elements.profileName.value = profile.tutor_name;
    }
    if (elements.profileAbout) {
      elements.profileAbout.value = profile.about_text;
    }
    if (elements.portfolioArticlesText) {
      elements.portfolioArticlesText.value = getPortfolioSection(0).text || "";
    }
    if (elements.portfolioProgramsText) {
      elements.portfolioProgramsText.value = getPortfolioSection(1).text || "";
    }
    if (elements.portfolioEventsText) {
      elements.portfolioEventsText.value = getPortfolioSection(2).text || "";
    }
  }
}

function renderSlots() {
  setupDaysDesktopScroll();
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
      const label = date.toLocaleDateString("ru-RU", { weekday: "short", day: "2-digit", month: "2-digit" });
      const isActive = state.selectedDay === dayKey ? "active" : "";
      return `<button class="day-pill ${isActive}" data-day="${dayKey}" type="button">${label}</button>`;
    })
    .join("");

  elements.slotsGrid.innerHTML = dayMap[state.selectedDay]
    .map((slot) => {
      const start = formatDate(slot.start_at, { hour: "2-digit", minute: "2-digit" });
      const end = formatDate(slot.end_at, { hour: "2-digit", minute: "2-digit" });
      return `
        <button class="slot-button" data-slot-id="${slot.id}" type="button">
          <strong>${start} - ${end}</strong>
          <span>Записаться</span>
          ${slot.discount_percent > 0 ? `<span class="slot-discount-badge">Скидка ${slot.discount_percent}%</span>` : ""}
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
        .map(
          (booking) => `
            <div class="list-item">
              <div>
                <strong>${escapeHtml(booking.user_first_name)}${booking.username ? ` (@${escapeHtml(booking.username)})` : ""}</strong>
                <span>${formatDate(booking.start_at, {
                  day: "2-digit",
                  month: "2-digit",
                  hour: "2-digit",
                  minute: "2-digit",
                })} - ${formatDate(booking.end_at, { hour: "2-digit", minute: "2-digit" })}</span>
                ${booking.discount_percent > 0 ? `<span class="discount-meta">Скидка ${booking.discount_percent}%</span>` : ""}
              </div>
              <div>
                <span>ID: ${booking.user_telegram_id}</span>
                <button class="danger-button" data-cancel-booking="${booking.id}" type="button">Отменить</button>
              </div>
            </div>
          `,
        )
        .join("")
    : "<p>Записей пока нет.</p>";
}

function renderStudents() {
  if (!elements.studentsList) {
    return;
  }

  elements.studentsList.innerHTML = state.students.length
    ? state.students
        .map(
          (student) => `
            <article class="student-card">
              <div>
                <strong>${escapeHtml(student.first_name)}${student.username ? ` (@${escapeHtml(student.username)})` : ""}</strong>
                <span>ID: ${student.telegram_id}</span>
                <span>Записей всего: ${student.bookings_count}</span>
                <span>${student.current_discount_label || "Скидки нет"}</span>
              </div>
              <div class="student-actions">
                <input
                  type="number"
                  min="0"
                  max="100"
                  step="1"
                  value="${student.admin_discount_percent ?? ""}"
                  placeholder="Скидка %"
                  data-student-discount-input="${student.id}"
                />
                <div class="student-buttons">
                  <button class="primary-button" data-save-student-discount="${student.id}" type="button">Сохранить</button>
                  <button class="danger-button" data-disable-student-discount="${student.id}" type="button">Убрать скидку</button>
                  <button class="secondary-button" data-auto-student-discount="${student.id}" type="button">Авто</button>
                </div>
              </div>
            </article>
          `,
        )
        .join("")
    : "<p>Пока нет учеников.</p>";
}

async function loadMe() {
  state.me = normalizeMeResponse(await apiFetch("/api/me"));
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
  const [slots, bookings, students] = await Promise.all([
    apiFetch("/api/admin/slots"),
    apiFetch("/api/admin/bookings"),
    apiFetch("/api/admin/students"),
  ]);
  state.adminSlots = slots;
  state.adminBookings = bookings;
  state.students = students;
  renderAdminSlots();
  renderAdminBookings();
  renderStudents();
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
      tutor_name: elements.profileName?.value.trim() || state.me.profile.tutor_name,
      about_text: elements.profileAbout?.value.trim() || state.me.profile.about_text,
      portfolio_articles_text: elements.portfolioArticlesText?.value.trim() || getPortfolioSection(0).text,
      portfolio_programs_text: elements.portfolioProgramsText?.value.trim() || getPortfolioSection(1).text,
      portfolio_events_text: elements.portfolioEventsText?.value.trim() || getPortfolioSection(2).text,
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
  await apiFetch("/api/admin/profile/photo", { method: "POST", body: formData });
  elements.photoForm.reset();
  await refreshAll();
}

async function uploadPortfolioPhoto(section, fileInput, formElement) {
  const file = fileInput.files[0];
  if (!file) {
    return;
  }
  const formData = new FormData();
  formData.append("photo", file);
  await apiFetch(`/api/admin/profile/portfolio-photo/${section}`, { method: "POST", body: formData });
  formElement.reset();
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

async function updateStudentDiscount(userId, adminDiscountPercent) {
  const updatedStudent = await apiFetch(`/api/admin/students/${userId}/discount`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ admin_discount_percent: adminDiscountPercent }),
  });
  state.students = state.students.map((student) => (student.id === updatedStudent.id ? updatedStudent : student));
  renderStudents();
}

document.addEventListener("click", async (event) => {
  const dayButton = event.target.closest("[data-day]");
  if (dayButton) {
    state.selectedDay = dayButton.dataset.day;
    renderSlots();
    return;
  }

  const closePortfolio = event.target.closest("[data-close-portfolio]");
  if (closePortfolio) {
    closePortfolioModal();
    return;
  }

  const slotButton = event.target.closest("[data-slot-id]");
  if (slotButton) {
    const slot = state.slots.find((item) => String(item.id) === String(slotButton.dataset.slotId));
    const slotLabel = slot
      ? `${formatDate(slot.start_at, { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" })} - ${formatDate(slot.end_at, { hour: "2-digit", minute: "2-digit" })}`
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
    return;
  }

  const saveDiscountButton = event.target.closest("[data-save-student-discount]");
  if (saveDiscountButton) {
    const input = document.querySelector(
      `[data-student-discount-input="${saveDiscountButton.dataset.saveStudentDiscount}"]`,
    );
    const value = input?.value?.trim();
    if (!value) {
      notify("Введите процент скидки от 0 до 100.");
      return;
    }
    try {
      await updateStudentDiscount(saveDiscountButton.dataset.saveStudentDiscount, Number(value));
      notify("Скидка сохранена.");
    } catch (error) {
      notify(error.message);
    }
    return;
  }

  const disableDiscountButton = event.target.closest("[data-disable-student-discount]");
  if (disableDiscountButton) {
    try {
      await updateStudentDiscount(disableDiscountButton.dataset.disableStudentDiscount, 0);
      notify("Скидка отключена.");
    } catch (error) {
      notify(error.message);
    }
    return;
  }

  const autoDiscountButton = event.target.closest("[data-auto-student-discount]");
  if (autoDiscountButton) {
    try {
      await updateStudentDiscount(autoDiscountButton.dataset.autoStudentDiscount, null);
      notify("Возврат в автоматический режим выполнен.");
    } catch (error) {
      notify(error.message);
    }
  }
});

elements.profileForm?.addEventListener("submit", async (event) => {
  try {
    await saveProfile(event);
  } catch (error) {
    notify(error.message);
  }
});

elements.portfolioForm?.addEventListener("submit", async (event) => {
  try {
    await saveProfile(event);
  } catch (error) {
    notify(error.message);
  }
});

elements.photoForm?.addEventListener("submit", async (event) => {
  try {
    await uploadPhoto(event);
  } catch (error) {
    notify(error.message);
  }
});

elements.slotForm?.addEventListener("submit", async (event) => {
  try {
    await createSlot(event);
  } catch (error) {
    notify(error.message);
  }
});

elements.portfolioArticlesPhotoForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    await uploadPortfolioPhoto("articles", elements.portfolioArticlesPhotoFile, elements.portfolioArticlesPhotoForm);
  } catch (error) {
    notify(error.message);
  }
});

elements.portfolioProgramsPhotoForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    await uploadPortfolioPhoto("programs", elements.portfolioProgramsPhotoFile, elements.portfolioProgramsPhotoForm);
  } catch (error) {
    notify(error.message);
  }
});

elements.portfolioEventsPhotoForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    await uploadPortfolioPhoto("events", elements.portfolioEventsPhotoFile, elements.portfolioEventsPhotoForm);
  } catch (error) {
    notify(error.message);
  }
});

elements.refreshButton?.addEventListener("click", async () => {
  try {
    await refreshAll();
  } catch (error) {
    notify(error.message);
  }
});

elements.daysScrollLeft?.addEventListener("click", () => scrollDays(-1));
elements.daysScrollRight?.addEventListener("click", () => scrollDays(1));
elements.inviteFriendButton?.addEventListener("click", async () => {
  try {
    await inviteFriend();
  } catch (error) {
    notify(error.message);
  }
});
elements.openPortfolioButton?.addEventListener("click", openPortfolioModal);
elements.closePortfolioButton?.addEventListener("click", closePortfolioModal);
elements.toggleStudentsButton?.addEventListener("click", () => {
  elements.studentsPanel?.classList.toggle("hidden");
});

window.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    closePortfolioModal();
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
