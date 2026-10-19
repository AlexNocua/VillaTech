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
    var expanded = false;
    var more = catalog.querySelector("[data-catalog-more]");

    function normalize(value) {
        return String(value || "")
            .toLocaleLowerCase("es")
            .normalize("NFD")
            .replace(/[\u0300-\u036f]/g, "")
            .trim();
    }

    function updateCatalog() {
        var query = normalize(search ? search.value : "");
        var orderedCards = cards.slice().sort(function (first, second) {
            if (sort && sort.value === "name") {
                return normalize(first.dataset.name).localeCompare(normalize(second.dataset.name), "es");
            }

            return Number(second.dataset.featured || 0) - Number(first.dataset.featured || 0);
        });

        var matched = orderedCards.filter(function(card) {
            return (activeCategory === "all" || card.dataset.category === activeCategory)
                && (!query || normalize(card.dataset.name).indexOf(query) !== -1);
        });
        orderedCards.forEach(function(card) {
            card.hidden = matched.indexOf(card) === -1 || (!expanded && matched.indexOf(card) >= 5);
            grid.appendChild(card);
        });
        var shown = expanded ? matched.length : Math.min(5, matched.length);
        if (count) count.textContent = "Mostrando " + shown + " de " + matched.length + " productos";
        if (empty) empty.hidden = matched.length !== 0;
        if (more) {
            more.hidden = matched.length <= 5;
            more.textContent = expanded ? "Ver menos productos" : "Ver más productos (" + (matched.length - shown) + ")";
            more.setAttribute("aria-expanded", String(expanded));
        }
    }

    filters.forEach(function (filter) {
        filter.addEventListener("click", function () {
            expanded = false;
            activeCategory = filter.dataset.catalogFilter || "all";
            filters.forEach(function (button) {
                var isActive = button === filter;
                button.classList.toggle("is-active", isActive);
                button.setAttribute("aria-pressed", String(isActive));
            });
            updateCatalog();
        });
    });

    if (search) search.addEventListener("input", function(){ expanded = false; updateCatalog(); });
    if (sort) sort.addEventListener("change", function(){ expanded = false; updateCatalog(); });
    if (more) more.addEventListener("click", function(){ expanded = !expanded; updateCatalog(); if (!expanded) { grid.scrollIntoView({block:"start"}); } });

    catalog.addEventListener("click", function (event) {
        var reset = event.target.closest("[data-catalog-reset]");
        if (reset) {
            activeCategory = "all";
            expanded = false;
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


    });

    var source = document.getElementById('catalog-product-data');
    var products = source ? JSON.parse(source.textContent) : [];
    var lookup = new Map(products.map(function(product){return [String(product.id),product];}));
    var dialog = document.getElementById('catalog-product-dialog');
    var selected = document.getElementById('contact-reference-product');
    var form = document.querySelector('[data-contact-form]');
    var appliedText = '';
    function selection(product){
        var panel=document.getElementById('contact-product-selection');
        if(!panel)return;
        panel.hidden=!selected.value;
        document.getElementById('contact-selected-product-name').textContent=product ? 'Producto: '+product.name : 'Producto de referencia seleccionado';
        document.getElementById('contact-selected-category').textContent=product ? 'Categoría: '+product.category : '';
    }
    if(selected){var initial=lookup.get(selected.value);selection(initial);if(initial)appliedText=initial.quote_text;}
    function quoteProduct(product){
        var message=document.getElementById('contact-message');
        var current=message.value,notes='';
        if(appliedText && current.indexOf(appliedText)===0)notes=current.slice(appliedText.length);
        else if(current.trim())notes='\n\nDetalles adicionales:\n'+current;
        message.value=product.quote_text+notes;appliedText=product.quote_text;
        selected.value=product.id;selection(product);
        document.getElementById('contact-service').value='impresion-3d';
        message.dispatchEvent(new Event('input',{bubbles:true}));
        if(dialog && dialog.open)dialog.close();
        document.getElementById('contacto').scrollIntoView({block:'start',behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'});
        message.focus({preventScroll:true});
    }
    document.addEventListener('click',function(event){
        var quote=event.target.closest('[data-catalog-quote]');
        if(quote && selected){var product=lookup.get(quote.dataset.productId);if(product){event.preventDefault();quoteProduct(product);}return;}
        var open=event.target.closest('[data-product-open]');
        if(!open){var card=event.target.closest('[data-product-card]');if(card && !event.target.closest('a,button,summary,input,select,textarea'))open=card;}
        if(open && dialog && dialog.showModal){
            var product=lookup.get(open.dataset.productOpen || open.dataset.productId);if(!product)return;
            event.preventDefault();document.getElementById('catalog-dialog-title').textContent=product.name;
            document.getElementById('catalog-dialog-category').textContent=product.category;
            document.getElementById('catalog-dialog-description').textContent=product.description;
            document.getElementById('catalog-dialog-price').textContent='Precio de referencia: '+new Intl.NumberFormat('es-CO',{style:'currency',currency:'COP',maximumFractionDigits:0}).format(Number(product.price));
            var image=document.getElementById('catalog-dialog-image');image.hidden=!product.image;if(product.image)image.src=product.image;else image.removeAttribute('src');image.alt=product.name;
            var button=document.getElementById('catalog-dialog-quote');button.dataset.productId=product.id;button.href='?product='+encodeURIComponent(product.id)+'#contacto';
            if(!dialog.open)dialog.showModal();
        }
    });
    dialog && dialog.querySelector('[data-product-close]').addEventListener('click',function(){dialog.close();});
    document.getElementById('contact-clear-product')?.addEventListener('click',function(){selected.value='';selection(null);appliedText='';});
    form?.addEventListener('catalog-selection-reset',function(){selected.value='';selection(null);appliedText='';});
    updateCatalog();
}());
