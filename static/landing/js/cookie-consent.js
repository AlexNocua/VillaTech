(function () {
    "use strict";

    var storageKey = "villatech-consent-v1";
    var version = 1;
    var banner = document.querySelector("[data-cookie-banner]");
    var consentDialog = document.querySelector("[data-consent-dialog]");
    var consentForm = document.querySelector("[data-consent-form]");
    var analyticsControl = document.querySelector("[data-consent-analytics]");
    var marketingControl = document.querySelector("[data-consent-marketing]");

    function readConsent() {
        try {
            var stored = JSON.parse(localStorage.getItem(storageKey));
            return stored && stored.version === version ? stored : null;
        } catch (error) {
            return null;
        }
    }

    function openDialog(dialog) {
        if (!dialog) return;
        if (typeof dialog.showModal === "function") {
            if (!dialog.open) dialog.showModal();
        } else {
            dialog.setAttribute("open", "");
        }
    }

    function closeDialog(dialog) {
        if (!dialog) return;
        if (typeof dialog.close === "function") dialog.close();
        else dialog.removeAttribute("open");
    }

    function saveConsent(analytics, marketing) {
        var preference = {
            version: version,
            necessary: true,
            analytics: Boolean(analytics),
            marketing: Boolean(marketing),
            updatedAt: new Date().toISOString()
        };

        try {
            localStorage.setItem(storageKey, JSON.stringify(preference));
        } catch (error) {
            /* El sitio continúa usando únicamente sus funciones esenciales. */
        }

        if (banner) banner.hidden = true;
        closeDialog(consentDialog);
        window.dispatchEvent(new CustomEvent("villatech:consentchange", { detail: preference }));
    }

    function syncForm() {
        var current = readConsent();
        if (analyticsControl) analyticsControl.checked = Boolean(current && current.analytics);
        if (marketingControl) marketingControl.checked = Boolean(current && current.marketing);
    }

    function openPreferences() {
        syncForm();
        document.querySelectorAll("[data-legal-dialog]").forEach(function (dialog) {
            closeDialog(dialog);
        });
        openDialog(consentDialog);
    }

    document.addEventListener("click", function (event) {
        var actionButton = event.target.closest("[data-cookie-action]");
        if (actionButton) {
            var action = actionButton.dataset.cookieAction;
            if (action === "all") saveConsent(true, true);
            if (action === "necessary") saveConsent(false, false);
            if (action === "configure") openPreferences();
            return;
        }

        var settingsButton = event.target.closest("[data-cookie-settings]");
        if (settingsButton) {
            openPreferences();
            return;
        }

        var legalButton = event.target.closest("[data-legal-open]");
        if (legalButton) {
            var dialog = document.querySelector('[data-legal-dialog="' + legalButton.dataset.legalOpen + '"]');
            openDialog(dialog);
            return;
        }

        var closeButton = event.target.closest("[data-dialog-close]");
        if (closeButton) closeDialog(closeButton.closest("dialog"));
    });

    document.querySelectorAll("dialog").forEach(function (dialog) {
        dialog.addEventListener("click", function (event) {
            if (event.target === dialog) closeDialog(dialog);
        });
    });

    if (consentForm) {
        consentForm.addEventListener("submit", function (event) {
            event.preventDefault();
            saveConsent(analyticsControl && analyticsControl.checked, marketingControl && marketingControl.checked);
        });
    }

    var current = readConsent();
    if (banner) banner.hidden = Boolean(current);
    if (current) {
        window.dispatchEvent(new CustomEvent("villatech:consentchange", { detail: current }));
    }
}());
