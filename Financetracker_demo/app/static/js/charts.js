(function () {
  "use strict";
  var INK = "#334155";
  var GRID = "#e2e8f0";
  var money = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 });
  function showMessage(canvas, text) {
    var box = canvas.closest(".chart-box");
    if (box) box.innerHTML = '<p class="empty">' + text + "</p>";
  }
  function loadJson(url) {
    return fetch(url, { headers: { Accept: "application/json" } }).then(function (response) {
      if (!response.ok) throw new Error("Request failed");
      return response.json();
    });
  }
  function drawCategoryChart() {
    var canvas = document.getElementById("categoryChart");
    if (!canvas) return;
    loadJson(canvas.dataset.url)
      .then(function (data) {
        if (!data.values.length) {
          showMessage(canvas, "No spending recorded this month yet.");
          return;
        }
        new Chart(canvas, {
          type: "doughnut",
          data: {
            labels: data.labels,
            datasets: [{
              data: data.values,
              backgroundColor: data.colours,
              borderColor: "#ffffff",
              borderWidth: 2,
            }],
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: "62%",
            plugins: {
              legend: { position: "bottom", labels: { color: INK, boxWidth: 12, padding: 14 } },
              tooltip: {
                callbacks: {
                  label: function (item) {
                    var share = data.total ? Math.round((item.parsed / data.total) * 100) : 0;
                    return " " + item.label + ": Rs. " + money.format(item.parsed) + " (" + share + "%)";
                  },
                },
              },
            },
          },
        });
      })
      .catch(function () {
        showMessage(canvas, "The chart could not be loaded.");
      });
  }
  function drawTrendChart() {
    var canvas = document.getElementById("trendChart");
    if (!canvas) return;
    loadJson(canvas.dataset.url)
      .then(function (data) {
        new Chart(canvas, {
          type: "line",
          data: {
            labels: data.labels,
            datasets: [
              {
                label: "Money in",
                data: data.income,
                borderColor: "#22c55e",
                backgroundColor: "rgba(34,197,94,.12)",
                fill: true,
                tension: 0.3,
                pointRadius: 3,
              },
              {
                label: "Money out",
                data: data.expense,
                borderColor: "#ef4444",
                backgroundColor: "rgba(239,68,68,.12)",
                fill: true,
                tension: 0.3,
                pointRadius: 3,
              },
            ],
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: "index", intersect: false },
            scales: {
              x: { grid: { display: false }, ticks: { color: INK } },
              y: {
                beginAtZero: true,
                grid: { color: GRID },
                ticks: {
                  color: INK,
                  callback: function (value) { return "Rs. " + money.format(value); },
                },
              },
            },
            plugins: {
              legend: { position: "bottom", labels: { color: INK, boxWidth: 12, padding: 14 } },
              tooltip: {
                callbacks: {
                  label: function (item) {
                    return " " + item.dataset.label + ": Rs. " + money.format(item.parsed.y);
                  },
                },
              },
            },
          },
        });
      })
      .catch(function () {
        showMessage(canvas, "The chart could not be loaded.");
      });
  }
  document.addEventListener("DOMContentLoaded", function () {
    if (typeof Chart === "undefined") return;
    drawCategoryChart();
    drawTrendChart();
  });
})();
