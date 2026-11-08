/**
 * AI Job Mentor for Informal Workers — Main JavaScript
 * Dark mode, language selector, animations, voice search, UI helpers
 */

// ── Dark Mode ──────────────────────────────────────────────────────────────
(function initDarkMode() {
  const saved = localStorage.getItem("darkMode");
  const body = document.getElementById("app-body");
  const html = document.getElementById("html-root");
  if (saved === "true" || (saved === null && window.matchMedia("(prefers-color-scheme: dark)").matches)) {
    body?.classList.add("dark-mode");
    html?.setAttribute("data-bs-theme", "dark");
    updateDarkModeIcon(true);
  }
})();

function toggleDarkMode() {
  const body = document.getElementById("app-body");
  const html = document.getElementById("html-root");
  const isDark = body?.classList.toggle("dark-mode");
  html?.setAttribute("data-bs-theme", isDark ? "dark" : "light");
  localStorage.setItem("darkMode", isDark ? "true" : "false");
  updateDarkModeIcon(isDark);
}

function updateDarkModeIcon(isDark) {
  const icon = document.getElementById("darkModeIcon");
  if (icon) icon.className = isDark ? "bi bi-sun-fill" : "bi bi-moon-fill";
}

// ── Language Selector ──────────────────────────────────────────────────────
const LANG_LABELS = { en: "EN", hi: "HI", te: "TE" };

function setLanguage(lang) {
  localStorage.setItem("appLang", lang);
  const label = document.getElementById("lang-label");
  if (label) label.textContent = LANG_LABELS[lang] || lang.toUpperCase();
  // If user is logged in, persist via profile page; for now just update chatbot if open
  if (window.currentLang !== undefined) window.currentLang = lang;
  // Refresh chatbot lang buttons
  document.querySelectorAll(".lang-btn").forEach(btn => btn.classList.remove("active"));
  document.querySelectorAll(".lang-btn").forEach(btn => {
    if (btn.textContent.trim() === lang.toUpperCase()) btn.classList.add("active");
  });
}

// Restore saved language
(function() {
  const lang = localStorage.getItem("appLang");
  if (lang && LANG_LABELS[lang]) {
    const label = document.getElementById("lang-label");
    if (label) label.textContent = LANG_LABELS[lang];
  }
})();

// ── Intersection Observer — Scroll Animations ──────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  const animated = document.querySelectorAll(".animate-slide-up, .animate-fade-in, .animate-fade-in-left, .animate-fade-in-right");
  if (!animated.length) return;

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.style.animationPlayState = "running";
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.12 });

  animated.forEach(el => {
    el.style.animationPlayState = "paused";
    observer.observe(el);
  });
});

// ── Auto-dismiss Flash Messages ─────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  const alerts = document.querySelectorAll("#flash-container .alert");
  alerts.forEach(alert => {
    setTimeout(() => {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
      bsAlert?.close();
    }, 4500);
  });
});

// ── Navbar Scroll Effect ───────────────────────────────────────────────────
window.addEventListener("scroll", () => {
  const navbar = document.getElementById("main-navbar");
  if (!navbar) return;
  if (window.scrollY > 20) {
    navbar.classList.add("scrolled");
    navbar.style.boxShadow = "0 2px 20px rgba(0,0,0,.1)";
  } else {
    navbar.classList.remove("scrolled");
    navbar.style.boxShadow = "";
  }
}, { passive: true });

// ── Tooltip Initialization ─────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  const tooltipEls = document.querySelectorAll('[data-bs-toggle="tooltip"]');
  tooltipEls.forEach(el => new bootstrap.Tooltip(el, { trigger: "hover" }));
});

// ── Smooth Count-Up Animation for Numbers ─────────────────────────────────
function animateCountUp(element, target, duration = 1200) {
  const start = performance.now();
  const step = (now) => {
    const elapsed = now - start;
    const progress = Math.min(elapsed / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
    element.textContent = Math.round(eased * target).toLocaleString("en-IN");
    if (progress < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

// ── Save Job Button Handler (global) ──────────────────────────────────────
document.addEventListener("click", async (e) => {
  const btn = e.target.closest(".save-job-btn");
  if (!btn) return;
  const jobId = btn.dataset.jobId;
  if (!jobId) return;
  btn.disabled = true;
  try {
    const res = await fetch(`/api/save_job/${jobId}`, { method: "POST" });
    if (res.status === 401) {
      window.location.href = "/login";
      return;
    }
    const data = await res.json();
    const icon = btn.querySelector("i") || btn;
    if (data.status === "saved") {
      if (icon.tagName === "I") icon.className = "bi bi-bookmark-fill text-primary";
      btn.title = "Remove from saved";
      showToast("Job saved!", "success");
    } else {
      if (icon.tagName === "I") icon.className = "bi bi-bookmark text-muted";
      btn.title = "Save job";
      showToast("Job removed from saved.", "info");
    }
  } catch (err) {
    showToast("Error saving job. Please try again.", "danger");
  } finally {
    btn.disabled = false;
  }
});

// ── Toast Notification ─────────────────────────────────────────────────────
function showToast(message, type = "info") {
  const existing = document.getElementById("toast-container");
  if (!existing) {
    const div = document.createElement("div");
    div.id = "toast-container";
    div.style.cssText = "position:fixed;bottom:24px;right:24px;z-index:9999;display:flex;flex-direction:column;gap:8px;";
    document.body.appendChild(div);
  }
  const container = document.getElementById("toast-container");
  const icons = { success: "check-circle-fill", danger: "exclamation-triangle-fill", info: "info-circle-fill", warning: "exclamation-circle-fill" };
  const toast = document.createElement("div");
  toast.className = `alert alert-${type} d-flex align-items-center gap-2 py-2 px-3 rounded-3 shadow-sm mb-0`;
  toast.style.cssText = "min-width:220px;max-width:320px;animation:fadeIn .25s ease;font-size:.875rem;";
  toast.innerHTML = `<i class="bi bi-${icons[type] || "info-circle-fill"}"></i>${message}`;
  container.appendChild(toast);
  setTimeout(() => { toast.style.opacity = "0"; toast.style.transition = "opacity .3s"; setTimeout(() => toast.remove(), 350); }, 3000);
}

// ── Voice Search (global helper used by jobs page and chatbot) ─────────────
function getSpeechRecognition() {
  return window.SpeechRecognition || window.webkitSpeechRecognition || null;
}

// ── Loading State for Forms ────────────────────────────────────────────────
document.addEventListener("submit", (e) => {
  const form = e.target;
  const submitBtn = form.querySelector('[type="submit"]');
  if (!submitBtn) return;
  const originalText = submitBtn.innerHTML;
  submitBtn.disabled = true;
  submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Processing...';
  // Re-enable after 10s as a safety net
  setTimeout(() => {
    submitBtn.disabled = false;
    submitBtn.innerHTML = originalText;
  }, 10000);
});

// ── Utility: debounce ──────────────────────────────────────────────────────
function debounce(fn, delay) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), delay);
  };
}

// ── Live Search Suggestion (jobs page search input) ───────────────────────
const searchInput = document.getElementById("search-input");
if (searchInput) {
  const suggestions = ["mason", "plumber", "weaver", "cook", "driver", "electrician", "tailor", "carpenter", "helper", "farmer"];
  searchInput.addEventListener("keyup", debounce(() => {
    const val = searchInput.value.toLowerCase().trim();
    if (!val || val.length < 2) return;
    // Could extend to show datalist/autocomplete here
  }, 300));
}

// ── Geolocation Helper ─────────────────────────────────────────────────────
function getCurrentLocationText(callback) {
  if (!navigator.geolocation) { callback(null, "Geolocation not supported"); return; }
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      fetch(`https://nominatim.openstreetmap.org/reverse?lat=${pos.coords.latitude}&lon=${pos.coords.longitude}&format=json`)
        .then(r => r.json())
        .then(data => {
          const a = data.address || {};
          const loc = [a.city || a.town || a.village, a.state].filter(Boolean).join(", ");
          callback(loc || `${pos.coords.latitude.toFixed(3)}, ${pos.coords.longitude.toFixed(3)}`, null);
        })
        .catch(() => callback(`${pos.coords.latitude.toFixed(3)}, ${pos.coords.longitude.toFixed(3)}`, null));
    },
    (err) => callback(null, "Location access denied")
  );
}

// ── Print / Share ──────────────────────────────────────────────────────────
function printPage() { window.print(); }
