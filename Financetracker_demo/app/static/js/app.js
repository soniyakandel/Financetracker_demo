(function () {
  "use strict";
  function setupSidebar() {
    var sidebar = document.getElementById("sidebar");
    var backdrop = document.querySelector(".sidebar-backdrop");
    if (!sidebar) return;
    function toggle() {
      var open = sidebar.classList.toggle("is-open");
      if (backdrop) backdrop.hidden = !open;
    }
    document.querySelectorAll("[data-sidebar-toggle]").forEach(function (el) {
      el.addEventListener("click", toggle);
    });
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && sidebar.classList.contains("is-open")) toggle();
    });
  }
  function setupFlashes() {
    document.querySelectorAll("[data-dismiss]").forEach(function (button) {
      button.addEventListener("click", function () {
        var flash = button.closest(".flash");
        if (flash) flash.remove();
      });
    });
  }
  function setupConfirms() {
    document.querySelectorAll("form[data-confirm]").forEach(function (form) {
      form.addEventListener("submit", function (event) {
        if (!window.confirm(form.getAttribute("data-confirm"))) {
          event.preventDefault();
        }
      });
    });
  }
  function scorePassword(value) {
    var score = 0;
    if (value.length >= 8) score++;
    if (value.length >= 12) score++;
    if (/[a-z]/.test(value) && /[A-Z]/.test(value)) score++;
    if (/[0-9]/.test(value) && /[^A-Za-z0-9]/.test(value)) score++;
    return score;
  }
  function setupStrengthMeter() {
    var input = document.querySelector("[data-strength-input]");
    var bar = document.querySelector("[data-strength-bar]");
    var text = document.querySelector("[data-strength-text]");
    if (!input || !bar) return;
    var labels = ["Very weak", "Weak", "Fair", "Good", "Strong"];
    input.addEventListener("input", function () {
      var score = scorePassword(input.value);
      bar.setAttribute("data-score", input.value ? String(score) : "0");
      if (text) {
        text.textContent = input.value
          ? "Strength: " + labels[score]
          : "These rules are checked again on the server.";
      }
    });
  }
  function setupPasswordToggles() {
    document.querySelectorAll("[data-password-toggle]").forEach(function (button) {
      var input = document.getElementById(button.getAttribute("aria-controls"));
      if (!input) return;
      button.hidden = false;
      button.addEventListener("click", function () {
        var reveal = input.type === "password";
        var caret = input.selectionStart;
        input.type = reveal ? "text" : "password";
        button.setAttribute("aria-pressed", reveal ? "true" : "false");
        button.setAttribute("aria-label", reveal ? "Hide password" : "Show password");
        button.setAttribute("title", reveal ? "Hide password" : "Show password");
        input.focus();
        if (caret !== null) input.setSelectionRange(caret, caret);
      });
    });
  }
  function setupAutoFilters() {
    document.querySelectorAll("[data-auto-submit]").forEach(function (field) {
      field.addEventListener("change", function () {
        if (field.form) field.form.submit();
      });
    });
  }
  function setupOtpInput() {
    var input = document.querySelector("[data-otp-input]");
    if (!input) return;
    input.addEventListener("input", function () {
      input.value = input.value.replace(/\D/g, "").slice(0, 6);
    });
    input.focus();
  }
  document.addEventListener("DOMContentLoaded", function () {
    setupSidebar();
    setupFlashes();
    setupConfirms();
    setupStrengthMeter();
    setupPasswordToggles();
    setupAutoFilters();
    setupOtpInput();
  });
})();
