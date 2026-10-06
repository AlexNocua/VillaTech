(function () {
    "use strict";

    var storageKey = "landing-theme";
    var root = document.documentElement;
    var toggles = document.querySelectorAll("[data-theme-toggle]");
    var systemPreference = window.matchMedia("(prefers-color-scheme: dark)");

    function getStoredTheme() {
        try {
            var storedTheme = localStorage.getItem(storageKey);
            return storedTheme === "light" || storedTheme === "dark" ? storedTheme : null;
        } catch (error) {
            return null;
        }
    }

    function updateControls(theme) {
        var nextTheme = theme === "dark" ? "claro" : "oscuro";

        toggles.forEach(function (toggle) {
            toggle.setAttribute("aria-label", "Activar tema " + nextTheme);
            toggle.setAttribute("title", "Activar tema " + nextTheme);
        });
    }

    function updateBrowserColor(theme) {
        var metaTheme = document.querySelector('meta[name="theme-color"]');
        if (metaTheme) {
            metaTheme.setAttribute("content", theme === "dark" ? "#030B12" : "#FFFFFF");
        }
    }

    function applyTheme(theme, persist) {
        root.dataset.theme = theme;
        root.style.colorScheme = theme;
        updateControls(theme);
        updateBrowserColor(theme);

        if (persist) {
            try {
                localStorage.setItem(storageKey, theme);
            } catch (error) {
                /* La navegación continúa aunque el almacenamiento esté bloqueado. */
            }
        }
    }

    toggles.forEach(function (toggle) {
        toggle.addEventListener("click", function () {
            var nextTheme = root.dataset.theme === "dark" ? "light" : "dark";
            applyTheme(nextTheme, true);
        });
    });

    function followSystemTheme(event) {
        if (!getStoredTheme()) {
            applyTheme(event.matches ? "dark" : "light", false);
        }
    }

    if (typeof systemPreference.addEventListener === "function") {
        systemPreference.addEventListener("change", followSystemTheme);
    } else if (typeof systemPreference.addListener === "function") {
        systemPreference.addListener(followSystemTheme);
    }

    applyTheme(root.dataset.theme === "dark" ? "dark" : "light", false);
}());
