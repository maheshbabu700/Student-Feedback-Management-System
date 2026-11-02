/* Chart rendering for the Dashboard and Reports pages.
 *
 * Data is supplied by Flask as JSON inside <script id="chart-data" type="application/json">.
 * Each <canvas data-chart="rating|faculty|course"> is drawn from that data.
 * If Chart.js could not be loaded (e.g. no internet), a message is shown instead.
 */
(function () {
    "use strict";

    var canvases = document.querySelectorAll("canvas[data-chart]");
    if (!canvases.length) { return; }

    function showFallback() {
        document.querySelectorAll("[data-chart-error]").forEach(function (el) { el.hidden = false; });
        canvases.forEach(function (canvas) {
            var box = canvas.closest(".chart-box");
            if (box) { box.hidden = true; }
        });
    }

    if (typeof window.Chart === "undefined") { showFallback(); return; }

    var data = {};
    try {
        var source = document.getElementById("chart-data");
        data = source ? JSON.parse(source.textContent) : {};
    } catch (error) {
        showFallback();
        return;
    }

    // Colours follow the CSS design tokens.
    var css = getComputedStyle(document.documentElement);
    function token(name, fallback) {
        var value = css.getPropertyValue(name).trim();
        return value || fallback;
    }
    var COLORS = {
        navy: token("--navy-700", "#1f3f73"),
        teal: token("--teal-600", "#23707a"),
        gold: token("--gold-500", "#b8913f"),
        text: token("--text-muted", "#5f6a80"),
        grid: token("--border", "#e4dfd2"),
        tooltip: token("--navy-950", "#0b1a33")
    };

    Chart.defaults.font.family = token("--font-body", "system-ui, sans-serif");
    Chart.defaults.font.size = 12.5;
    Chart.defaults.color = COLORS.text;

    function plural(n, word) { return n + " " + word + (n === 1 ? "" : "s"); }

    function baseOptions(yTitle, yMax) {
        return {
            responsive: true,
            maintainAspectRatio: false,
            layout: { padding: { top: 6 } },
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: COLORS.tooltip,
                    titleColor: "#ffffff",
                    bodyColor: "#e6ebf4",
                    padding: 10,
                    cornerRadius: 8,
                    displayColors: false
                }
            },
            scales: {
                x: { grid: { display: false }, border: { color: COLORS.grid } },
                y: {
                    beginAtZero: true,
                    max: yMax,
                    title: { display: true, text: yTitle, color: COLORS.text },
                    grid: { color: COLORS.grid },
                    border: { display: false },
                    ticks: { precision: 0, stepSize: yMax ? 1 : undefined }
                }
            }
        };
    }

    function drawRating(canvas) {
        var rows = data.rating || [];
        var options = baseOptions("Submissions");
        options.plugins.tooltip.callbacks = {
            title: function (items) { return items[0].label; },
            label: function (ctx) { return plural(ctx.parsed.y, "submission"); }
        };
        new Chart(canvas, {
            type: "bar",
            data: {
                labels: rows.map(function (r) { return plural(r.rating, "Star"); }),
                datasets: [{
                    data: rows.map(function (r) { return r.count; }),
                    backgroundColor: COLORS.navy,
                    hoverBackgroundColor: COLORS.gold,
                    borderRadius: 6,
                    maxBarThickness: 56
                }]
            },
            options: options
        });
    }

    function drawAverage(canvas, rows, color, noun) {
        var options = baseOptions("Average rating (out of 5)", 5);
        options.plugins.tooltip.callbacks = {
            title: function (items) { return noun + " " + items[0].label; },
            label: function (ctx) {
                var row = rows[ctx.dataIndex];
                return [
                    "Average: " + Number(ctx.parsed.y).toFixed(2) + " / 5",
                    plural(row.submission_count, "submission")
                ];
            }
        };
        new Chart(canvas, {
            type: "bar",
            data: {
                labels: rows.map(function (r) { return r.category; }),
                datasets: [{
                    data: rows.map(function (r) { return r.average_rating; }),
                    backgroundColor: color,
                    hoverBackgroundColor: COLORS.gold,
                    borderRadius: 6,
                    maxBarThickness: 56
                }]
            },
            options: options
        });
    }

    canvases.forEach(function (canvas) {
        var kind = canvas.getAttribute("data-chart");
        try {
            if (kind === "rating") {
                drawRating(canvas);
            } else if (kind === "faculty") {
                drawAverage(canvas, data.faculty || [], COLORS.teal, "Faculty");
            } else if (kind === "course") {
                drawAverage(canvas, data.course || [], COLORS.navy, "Course");
            }
        } catch (error) {
            if (window.console) { console.error("Chart failed:", kind, error); }
            showFallback();
        }
    });
})();
