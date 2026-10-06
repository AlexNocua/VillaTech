(function () {
    "use strict";

    try {
        var savedTheme = localStorage.getItem("landing-theme");
        var systemTheme = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
        var activeTheme = savedTheme === "light" || savedTheme === "dark" ? savedTheme : systemTheme;
        document.documentElement.dataset.theme = activeTheme;
        document.documentElement.style.colorScheme = activeTheme;
    } catch (error) {
        document.documentElement.dataset.theme = "light";
        document.documentElement.style.colorScheme = "light";
    }
}());
