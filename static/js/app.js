/* Shared UI behaviour: mobile navigation and show/hide password. */
(function () {
    "use strict";

    // ----- Mobile sidebar -----
    var toggle = document.getElementById("menu-toggle");
    var sidebar = document.getElementById("sidebar");
    var scrim = document.getElementById("scrim");

    function setMenu(open) {
        if (!toggle || !sidebar || !scrim) { return; }
        sidebar.classList.toggle("is-open", open);
        scrim.hidden = !open;
        toggle.setAttribute("aria-expanded", String(open));
        toggle.setAttribute("aria-label", open ? "Close navigation" : "Open navigation");
    }

    if (toggle && sidebar && scrim) {
        toggle.addEventListener("click", function () {
            setMenu(!sidebar.classList.contains("is-open"));
        });
        scrim.addEventListener("click", function () { setMenu(false); });
        document.addEventListener("keydown", function (event) {
            if (event.key === "Escape" && sidebar.classList.contains("is-open")) {
                setMenu(false);
                toggle.focus();
            }
        });
        window.addEventListener("resize", function () {
            if (window.innerWidth > 960) { setMenu(false); }
        });
    }

    // ----- Show / hide password -----
    var pwToggle = document.getElementById("password-toggle");
    var pwInput = document.getElementById("password");

    if (pwToggle && pwInput) {
        pwToggle.hidden = false; // Only shown when JavaScript is running.
        pwToggle.addEventListener("click", function () {
            var show = pwInput.type === "password";
            pwInput.type = show ? "text" : "password";
            pwToggle.setAttribute("aria-pressed", String(show));
            pwToggle.setAttribute("aria-label", show ? "Hide password" : "Show password");
            var use = pwToggle.querySelector("use");
            if (use) { use.setAttribute("href", show ? "#i-eye-off" : "#i-eye"); }
        });
    }
})();
