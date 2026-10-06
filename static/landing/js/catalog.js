(function () {
    "use strict";

    var catalog = document.querySelector("[data-catalog]");
    if (!catalog) return;

    var grid = catalog.querySelector("[data-catalog-grid]");
    var cards = Array.prototype.slice.call(catalog.querySelectorAll("[data-product-card]"));
    var search = catalog.querySelector("[data-catalog-search]");
    var sort = catalog.querySelector("[data-catalog-sort]");
    var count = catalog.querySelector("[data-catalog-count]");
    var empty = catalog.querySelector("[data-catalog-empty]");
    var filters = Array.prototype.slice.call(catalog.querySelectorAll("[data-catalog-filter]"));
    var activeCategory = "all";

    function normalize(value) {
        return String(value || "")
            .toLocaleLowerCase("es")
            .normalize("NFD")
            .replace(/[\u0300-\u036f]/g, "")
            .trim();
    }

    function updateCatalog() {
        var query = normalize(search ? search.value : "");
        var visible = cards.filter(function (card) {
            var categoryMatches = activeCategory === "all" || card.dataset.category === activeCategory;
            var queryMatches = !query || normalize(card.dataset.name).indexOf(query) !== -1;
            var shouldShow = categoryMatches && queryMatches;
            card.hidden = !shouldShow;
            return shouldShow;
        });

        var orderedCards = cards.slice().sort(function (first, second) {
            if (sort && sort.value === "name") {
                return normalize(first.dataset.name).localeCompare(normalize(second.dataset.name), "es");
            }

            return Number(second.dataset.featured || 0) - Number(first.dataset.featured || 0);
        });

        orderedCards.forEach(function (card) {
            grid.appendChild(card);
        });

        if (count) {
            count.textContent = visible.length + (visible.length === 1 ? " producto disponible" : " productos disponibles");
        }
        if (empty) empty.hidden = visible.length !== 0;
    }

    filters.forEach(function (filter) {
        filter.addEventListener("click", function () {
            activeCategory = filter.dataset.catalogFilter || "all";
            filters.forEach(function (button) {
                var isActive = button === filter;
                button.classList.toggle("is-active", isActive);
                button.setAttribute("aria-pressed", String(isActive));
            });
            updateCatalog();
        });
    });

    if (search) search.addEventListener("input", updateCatalog);
    if (sort) sort.addEventListener("change", updateCatalog);

    catalog.addEventListener("click", function (event) {
        var reset = event.target.closest("[data-catalog-reset]");
        if (reset) {
            activeCategory = "all";
            if (search) search.value = "";
            filters.forEach(function (button) {
                var isAll = button.dataset.catalogFilter === "all";
                button.classList.toggle("is-active", isAll);
                button.setAttribute("aria-pressed", String(isAll));
            });
            updateCatalog();
            search && search.focus();
            return;
        }

        var quote = event.target.closest("[data-catalog-quote]");
        if (!quote) return;

        var service = document.querySelector("#contact-service");
        var message = document.querySelector("#contact-message");
        var productName = quote.dataset.productName || "una impresión 3D";

        if (service) service.value = "impresion-3d";
        if (message && !message.value.trim()) {
            message.value = "Me interesa cotizar: " + productName + ".\n\nCantidad, medidas o detalles: ";
        }
    });

    updateCatalog();
}());
