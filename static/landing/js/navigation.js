(function () {
    "use strict";

    var header = document.querySelector("[data-site-header]");
    var toggle = document.querySelector("[data-nav-toggle]");
    var menu = document.querySelector("[data-nav-menu]");
    var links = document.querySelectorAll("[data-nav-link]");

    if (!header || !toggle || !menu) {
        return;
    }

    function setMenu(open) {
        toggle.setAttribute("aria-expanded", String(open));
        toggle.querySelector(".sr-only").textContent = open ? "Cerrar menú" : "Abrir menú";
        menu.classList.toggle("is-open", open);
        header.classList.toggle("is-menu-open", open);
        document.body.classList.toggle("nav-open", open);
    }

    toggle.addEventListener("click", function () {
        setMenu(toggle.getAttribute("aria-expanded") !== "true");
    });

    links.forEach(function (link) {
        link.addEventListener("click", function () {
            setMenu(false);
        });
    });

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape" && toggle.getAttribute("aria-expanded") === "true") {
            setMenu(false);
            toggle.focus();
        }
    });

    document.addEventListener("click", function (event) {
        if (toggle.getAttribute("aria-expanded") !== "true") {
            return;
        }

        if (!header.contains(event.target)) {
            setMenu(false);
        }
    });

    window.addEventListener("resize", function () {
        if (window.innerWidth > 940) {
            setMenu(false);
        }
    });

    function updateHeader() {
        header.classList.toggle("is-scrolled", window.scrollY > 18);
    }

    updateHeader();
    window.addEventListener("scroll", updateHeader, { passive: true });

    if ("IntersectionObserver" in window) {
        var sections = document.querySelectorAll("main section[id]");
        var observer = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (!entry.isIntersecting) {
                    return;
                }

                links.forEach(function (link) {
                    var active = link.getAttribute("href") === "#" + entry.target.id;
                    link.classList.toggle("is-active", active);

                    if (active) {
                        link.setAttribute("aria-current", "location");
                    } else {
                        link.removeAttribute("aria-current");
                    }
                });
            });
        }, {
            rootMargin: "-30% 0px -62%",
            threshold: 0
        });

        sections.forEach(function (section) {
            observer.observe(section);
        });
    }
}());
