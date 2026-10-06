import { createAdditivePrinter } from "./additive-printer.js";
import {
    animate,
    createScope,
    createTimeline,
    stagger,
    svg,
    utils
} from "../vendor/animejs/anime.esm.min.js";

const storyRoot = document.querySelector("main");
const storyElement = storyRoot?.querySelector("[data-scroll-story]");
const mobileSlot = document.getElementById('mobile-animation-stage');
const mobileQuery = window.matchMedia('(max-width: 1179px)');
function placeMobileStory() {
    if (!storyElement || !mobileSlot) return;
    if (mobileQuery.matches && !document.body.classList.contains('story-focus-mode')) {mobileSlot.appendChild(storyElement);}
    else {storyRoot.insertBefore(storyElement, storyRoot.firstChild);}
}
placeMobileStory();
mobileQuery.addEventListener('change', placeMobileStory);

if (storyRoot && storyElement) {
    document.documentElement.dataset.storyAnimations = "loading";

    const focusToggle = storyRoot.querySelector("[data-story-focus-toggle]");
    const focusLabel = focusToggle?.querySelector("[data-story-focus-label]");
    const focusRegions = [
        document.querySelector(".site-header"),
        ...storyRoot.querySelectorAll(":scope > section"),
        document.querySelector(".site-footer")
    ].filter(Boolean);
    const globalCleanupCallbacks = [];
    let storyFocusActive = false;
    let updateStoryBoundary = () => {};

    const setStoryFocusMode = (enabled) => {
        storyFocusActive = Boolean(enabled);
        document.body.classList.toggle("story-focus-mode", storyFocusActive);
        document.documentElement.dataset.storyFocus = storyFocusActive ? "active" : "page";
        storyElement.setAttribute("aria-hidden", storyFocusActive ? "false" : "true");
        // Portal outside hidden/inert sections while the full-screen viewer is open.
        placeMobileStory();
        if (storyFocusActive) storyElement.classList.remove('is-story-hidden');

        if (focusToggle) {
            focusToggle.setAttribute("aria-pressed", String(storyFocusActive));
            focusToggle.setAttribute(
                "aria-label",
                storyFocusActive ? "Volver a ver la página completa" : "Ver únicamente la animación"
            );
        }
        if (focusLabel) {
            focusLabel.textContent = storyFocusActive ? "Volver a la página" : "Ver solo animación";
        }

        focusRegions.forEach((region) => {
            if (storyFocusActive && !region.hasAttribute("inert")) {
                region.setAttribute("inert", "");
                region.dataset.storyFocusInert = "added";
            } else if (!storyFocusActive && region.dataset.storyFocusInert === "added") {
                region.removeAttribute("inert");
                delete region.dataset.storyFocusInert;
            }
        });

        requestAnimationFrame(updateStoryBoundary);
    };

    const handleFocusToggle = () => setStoryFocusMode(!storyFocusActive);
    const handleFocusEscape = (event) => {
        if (event.key === "Escape" && storyFocusActive) {
            event.preventDefault();
            setStoryFocusMode(false);
            focusToggle?.focus({ preventScroll: true });
        }
    };

    if (focusToggle) {
        focusToggle.addEventListener("click", handleFocusToggle);
        globalCleanupCallbacks.push(() => focusToggle.removeEventListener("click", handleFocusToggle));
    }
    document.addEventListener("keydown", handleFocusEscape);
    globalCleanupCallbacks.push(() => document.removeEventListener("keydown", handleFocusEscape));

    const stageContent = {
        idea: {
            index: "01",
            label: "IDEA",
            x: 73,
            scale: 0.92,
            kicker: "PUNTO DE PARTIDA",
            title: "Una necesidad se convierte en concepto.",
            description: "Escuchamos el objetivo, entendemos el contexto y definimos qué debe tomar forma.",
            metrics: [
                { value: "Brief", label: "Entrada" },
                { value: "Idea", label: "Proceso" },
                { value: "Meta", label: "Salida" }
            ],
            code: ["const idea = escuchar();", "objetivo.define();", "estado: explorando"]
        },
        design: {
            index: "02",
            label: "DISEÑO",
            x: 27,
            scale: 1,
            kicker: "DISEÑO Y PROTOTIPADO",
            title: "Geometría preparada para fabricar.",
            description: "Transformamos referencias y medidas en un modelo validable, funcional y listo para producción.",
            metrics: [
                { value: "mm", label: "Medidas" },
                { value: "±0,2", label: "Tolerancia" },
                { value: "CAD", label: "Validación" }
            ],
            code: ["modelo = trazar(idea);", "medidas.validar();", "estado: prototipo"]
        },
        print: {
            index: "03",
            label: "IMPRESIÓN 3D",
            x: 73,
            scale: 0.95,
            kicker: "FABRICACIÓN ADITIVA",
            title: "Capas que construyen una pieza real.",
            description: "La boquilla deposita material con precisión mientras controlamos geometría, adhesión y acabado.",
            metrics: [
                { value: "PLA", label: "Material" },
                { value: "0,20", label: "Capa mm" },
                { value: "0,40", label: "Boquilla mm" }
            ],
            code: ["printer.load('PLA');", "layers.build(68);", "estado: fabricando"]
        },
        solder: {
            index: "04",
            label: "CONEXIÓN",
            x: 27,
            scale: 1.03,
            kicker: "ELECTRÓNICA Y CONEXIÓN",
            title: "La señal une lo físico con lo digital.",
            description: "El cautín recorre el circuito, fija cada punto y convierte componentes aislados en un sistema conectado.",
            metrics: [
                { value: "350°", label: "Cautín" },
                { value: "PCB", label: "Circuito" },
                { value: "OK", label: "Continuidad" }
            ],
            code: ["iron.heat(350);", "circuit.trace(signal);", "estado: conectando"]
        },
        code: {
            index: "05",
            label: "DESARROLLO",
            x: 73,
            scale: 0.96,
            kicker: "DESARROLLO",
            title: "La lógica convierte el flujo en sistema.",
            description: "Construimos backend, interfaz e integraciones como módulos que pueden probarse, mantenerse y crecer.",
            metrics: [
                { value: "Django", label: "Backend" },
                { value: "API", label: "Integración" },
                { value: "Tests", label: "Calidad" }
            ],
            code: ["app = develop(solution);", "tests.run();", "estado: compilando"]
        },
        solution: {
            index: "06",
            label: "SOLUCIÓN",
            x: 27,
            scale: 0.9,
            kicker: "VALIDACIÓN",
            title: "Cada parte converge en una solución útil.",
            description: "Comprobamos que objeto, interfaz y proceso respondan al uso real antes de cerrar la entrega.",
            metrics: [
                { value: "Sí", label: "Funcional" },
                { value: "+", label: "Escalable" },
                { value: "KPI", label: "Medible" }
            ],
            code: ["result.validate();", "value = problem.solve();", "estado: funcional"]
        },
        support: {
            index: "07",
            label: "CLARIDAD",
            x: 73,
            scale: 0.87,
            kicker: "ALCANCE CLARO",
            title: "Resolvemos preguntas antes de construir.",
            description: "Alineamos el uso, el tiempo y la inversión para avanzar con decisiones técnicas comprensibles.",
            metrics: [
                { value: "Uso", label: "Objetivo" },
                { value: "Tiempo", label: "Plan" },
                { value: "Valor", label: "Inversión" }
            ],
            code: ["questions.resolve();", "scope.confirm();", "estado: preparado"]
        },
        launch: {
            index: "08",
            label: "LANZAMIENTO",
            x: 50,
            scale: 1.08,
            kicker: "ENTREGA",
            title: "Tu idea está lista para operar y evolucionar.",
            description: "Entregamos una solución funcional, documentada y preparada para su siguiente versión.",
            metrics: [
                { value: "Lista", label: "Solución" },
                { value: "Docs", label: "Entrega" },
                { value: "vNext", label: "Evolución" }
            ],
            code: ["project.deploy();", "idea.toReality();", "estado: listo"]
        }
    };

    const storyScope = createScope({
        root: storyRoot,
        mediaQueries: {
            reduceMotion: "(prefers-reduced-motion: reduce)",
            isSmall: "(max-width: 640px)",
            isCompact: "(max-width: 1179px)"
        }
    });

    storyScope.add((scope) => {
        const { reduceMotion, isSmall, isCompact } = scope.matches;
        const cleanupCallbacks = [];
        const sections = Array.from(storyRoot.querySelectorAll("[data-story-stage]"));
        const storyStop = storyRoot.querySelector("[data-story-stop]");
        const storyBreaks = Array.from(storyRoot.querySelectorAll("[data-story-break]"));
        const scenes = new Map(
            Array.from(storyElement.querySelectorAll("[data-story-scene]"))
                .map((scene) => [scene.dataset.storyScene, scene])
        );
        const statusIndex = storyElement.querySelector("[data-story-index]");
        const statusLabel = storyElement.querySelector("[data-story-label]");
        const storyFrame = storyElement.querySelector(".scroll-story__frame");
        const terminalLines = Array.from(storyElement.querySelectorAll("[data-story-code-line]"));
        const detailKicker = storyElement.querySelector("[data-story-kicker]");
        const detailTitle = storyElement.querySelector("[data-story-title]");
        const detailDescription = storyElement.querySelector("[data-story-description]");
        const metricValues = Array.from(storyElement.querySelectorAll("[data-story-metric-value]"));
        const metricLabels = Array.from(storyElement.querySelectorAll("[data-story-metric-label]"));
        const detailBlock = storyElement.querySelector(".scroll-story__detail");
        const textRecords = new Map();
        const textAnimations = new Map();
        let activeSection = null;
        let activeStage = null;
        let activeScene = null;
        let sceneTimeline = null;
        const printer=createAdditivePrinter(storyElement.querySelector('[data-additive-printer]'));
        cleanupCallbacks.push(()=>printer?.pause());

        const setTerminalStatic = (stage) => {
            const content = stageContent[stage] || stageContent.idea;
            if (statusIndex) statusIndex.textContent = content.index;
            if (statusLabel) statusLabel.textContent = content.label;
            terminalLines.forEach((line, index) => {
                line.textContent = content.code[index] || "";
            });
            if (detailKicker) detailKicker.textContent = content.kicker;
            if (detailTitle) detailTitle.textContent = content.title;
            if (detailDescription) detailDescription.textContent = content.description;
            metricValues.forEach((element, index) => {
                element.textContent = content.metrics[index]?.value || "";
            });
            metricLabels.forEach((element, index) => {
                element.textContent = content.metrics[index]?.label || "";
            });
            storyElement.style.setProperty("--story-x", `${isCompact ? 50 : content.x}%`);
            storyElement.style.setProperty("--story-scale", isCompact ? "0.82" : String(content.scale));
        };

        if (reduceMotion) {
            storyElement.dataset.stage = "idea";
            setTerminalStatic("idea");
            sections[0]?.classList.add("is-story-active");
            document.documentElement.dataset.storyAnimations = "static";
            return () => {};
        }

        const splitHeading = (heading) => {
            if (!heading || heading.dataset.wordsReady === "true") return [];

            const text = heading.textContent.trim();
            const words = text.split(/\s+/);
            const fragment = document.createDocumentFragment();

            heading.textContent = "";
            heading.setAttribute("aria-label", text);
            heading.dataset.wordsReady = "true";

            words.forEach((word, index) => {
                const span = document.createElement("span");
                span.className = "scroll-word";
                span.setAttribute("aria-hidden", "true");
                span.textContent = word;
                fragment.appendChild(span);
                if (index < words.length - 1) fragment.appendChild(document.createTextNode(" "));
            });

            heading.appendChild(fragment);
            return Array.from(heading.querySelectorAll(".scroll-word"));
        };

        const buildTextRecords = () => {
            sections.forEach((section) => {
                const isHero = section.id === "inicio";
                const heading = section.querySelector("h2");
                const words = isHero || heading?.classList.contains("sr-only") ? [] : splitHeading(heading);
                const copy = isHero
                    ? Array.from(section.querySelectorAll("[data-hero-copy-item]"))
                    : Array.from(section.querySelectorAll(
                        ".eyebrow, .section-heading > p, .section-heading--split > p, .bridge__content > p, .faq__intro > p, .contact__content > p"
                    )).filter((item) => !item.matches("h2"));

                copy.forEach((item) => item.classList.add("scroll-copy-active"));
                textRecords.set(section, { words, copy });
                utils.set([...words, ...copy], {
                    opacity: 0,
                    y: 22,
                    filter: "blur(7px)"
                });
            });
        };

        const revealSectionText = (section, direction) => {
            const record = textRecords.get(section);
            if (!record) return;

            const offset = direction >= 0 ? 26 : -26;
            const targets = [...record.words, ...record.copy];
            if (!targets.length) return;
            utils.set(targets, { opacity: 0, y: offset, filter: "blur(8px)" });

            animate(targets, {
                opacity: [0, 1],
                y: [offset, 0],
                filter: ["blur(8px)", "blur(0px)"],
                duration: 760,
                delay: stagger(isSmall ? 34 : 54),
                ease: "outExpo"
            });
        };

        const hideSectionText = (section, direction) => {
            const record = textRecords.get(section);
            if (!record) return;

            const targets = [...record.words, ...record.copy];
            if (!targets.length) return;
            animate(targets, {
                opacity: 0,
                y: direction >= 0 ? -18 : 18,
                filter: "blur(6px)",
                duration: 320,
                delay: stagger(12),
                ease: "inQuad"
            });
        };

        const scrambleText = (element, finalText, delay = 0) => {
            if (!element) return;

            const glyphs = "01<>/{ }[]#*=+";
            const state = { progress: 0 };

            textAnimations.get(element)?.pause();
            textAnimations.set(element, animate(state, {
                progress: 1,
                delay,
                duration: 620,
                ease: "outQuad",
                onUpdate: () => {
                    const visible = Math.floor(finalText.length * state.progress);
                    element.textContent = finalText
                        .split("")
                        .map((character, index) => {
                            if (character === " " || index < visible) return character;
                            return glyphs[Math.floor(Math.random() * glyphs.length)];
                        })
                        .join("");
                },
                onComplete: () => {
                    element.textContent = finalText;
                }
            }));
        };

        const updateTerminal = (stage) => {
            const content = stageContent[stage] || stageContent.idea;

            if (statusIndex) statusIndex.textContent = content.index;
            scrambleText(statusLabel, content.label);

            terminalLines.forEach((line, index) => {
                scrambleText(line, content.code[index] || "", index * 85);
            });

            animate(terminalLines, {
                opacity: [0, 1],
                x: [-14, 0],
                duration: 520,
                delay: stagger(90),
                ease: "outExpo"
            });
        };

        const updateDetails = (stage) => {
            const content = stageContent[stage] || stageContent.idea;

            scrambleText(detailKicker, content.kicker);
            scrambleText(detailTitle, content.title, 90);
            if (detailDescription) detailDescription.textContent = content.description;

            metricValues.forEach((element, index) => {
                scrambleText(element, content.metrics[index]?.value || "", 170 + index * 70);
            });
            metricLabels.forEach((element, index) => {
                element.textContent = content.metrics[index]?.label || "";
            });

            animate([detailDescription, ...metricLabels].filter(Boolean), {
                opacity: [0, 1],
                y: [10, 0],
                duration: 560,
                delay: stagger(55, { start: 150 }),
                ease: "outExpo"
            });

            animate(metricValues, {
                opacity: [0, 1],
                scale: [0.82, 1],
                duration: 620,
                delay: stagger(70, { start: 180 }),
                ease: "outBack(1.5)"
            });

            if (detailBlock) {
                animate(detailBlock, {
                    opacity: [0.65, 1],
                    x: [stageContent[stage]?.x < 50 ? -16 : 16, 0],
                    duration: 720,
                    ease: "outExpo"
                });
            }
        };

        const playScene = (stage) => {
            sceneTimeline?.pause();
            printer?.pause();
            const scene = scenes.get(stage);
            if (!scene) return;

            if (activeScene && activeScene !== scene) {
                animate(activeScene, {
                    opacity: 0,
                    scale: 0.88,
                    rotate: activeStage === "solder" ? -4 : 0,
                    duration: 360,
                    ease: "inQuad"
                });
            }

            const drawables = svg.createDrawable(scene.querySelectorAll("[data-story-draw]"));
            drawables.forEach((drawable) => {
                drawable.draw = "0 0";
            });

            const dots = scene.querySelectorAll("[data-story-dot]");
            utils.set(scene, { opacity: 0, scale: 0.84, rotate: stage === "code" ? -2 : 0 });
            utils.set(dots, { opacity: 0, scale: 0.25 });

            sceneTimeline = createTimeline({
                autoplay: false,
                defaults: { ease: "outExpo" }
            })
                .add(scene, {
                    opacity: [0, 1],
                    scale: [0.84, 1],
                    rotate: 0,
                    duration: 680
                }, 0)
                .add(drawables, {
                    draw: ["0 0", "0 1"],
                    duration: 920,
                    delay: stagger(72),
                    ease: "inOutQuad"
                }, 100)
                .add(dots, {
                    opacity: [0, 1],
                    scale: [0.25, 1],
                    duration: 420,
                    delay: stagger(65),
                    ease: "outBack(1.8)"
                }, 360);

            if (stage === "design") {
                sceneTimeline.add(scene,{skewY:[-3,0],duration:1100,ease:'outExpo'},0);
            }
            if (stage === "solution" || stage === "launch") {
                sceneTimeline.add(scene,{scale:[.84,1.04,1],duration:1000,ease:'outSine'},0);
            }
            if (stage === "idea") {
                sceneTimeline.add(scene.querySelector(".story-core"), {
                    scale: [0.72, 1.18, 1],
                    opacity: [0.4, 1],
                    duration: 780,
                    ease: "outElastic(1, .55)"
                }, 100);
            }

            if (stage === "print") {
                sceneTimeline.call(()=>printer?.play(),300);
            }

            if (stage === "solder") {
                const traceElements = scene.querySelectorAll("[data-solder-trace]");
                const traces = svg.createDrawable(traceElements);
                const motionPath = scene.querySelector("[data-solder-path]");
                const iron = scene.querySelector("[data-solder-iron]");
                const sparksGroup = scene.querySelector(".story-sparks");
                const sparks = scene.querySelectorAll("[data-solder-spark]");

                traces.forEach((trace) => {
                    trace.draw = "0 0";
                });

                if (motionPath && iron && sparksGroup) {
                    const { translateX, translateY } = svg.createMotionPath(motionPath);
                    utils.set(iron, { opacity: 0 });
                    utils.set(sparksGroup, { opacity: 0 });
                    utils.set(sparks, { x: 0, y: 0, opacity: 0 });

                    sceneTimeline
                        .add(traces, {
                            draw: ["0 0", "0 1"],
                            duration: 1900,
                            ease: "linear"
                        }, 360)
                        .add(iron, {
                            opacity: [0, 1],
                            translateX,
                            translateY,
                            duration: 1900,
                            ease: "linear"
                        }, 330)
                        .add(sparksGroup, {
                            opacity: [0, 1],
                            translateX,
                            translateY,
                            duration: 1900,
                            ease: "linear"
                        }, 330)
                        .add(sparks, {
                            opacity: [0, 1, 0],
                            x: () => utils.random(-24, 24),
                            y: () => utils.random(-30, 10),
                            duration: 520,
                            delay: stagger(75),
                            ease: "outQuad"
                        }, 1800);
                }
            }

            if (stage === "code") {
                const codeLines = scene.querySelectorAll("[data-code-line]");
                utils.set(codeLines, { opacity: 0, scaleX: 0 });
                sceneTimeline.add(codeLines, {
                    opacity: [0, 1],
                    scaleX: [0, 1],
                    duration: 460,
                    delay: stagger(110),
                    ease: "outExpo"
                }, 420);
            }

            sceneTimeline.init().play();
            activeScene = scene;
        };

        const activateSection = (section) => {
            if (!section || section === activeSection) return;

            const stage = section.dataset.storyStage || "idea";
            const previousIndex = activeSection ? sections.indexOf(activeSection) : -1;
            const nextIndex = sections.indexOf(section);
            const direction = previousIndex === -1 || nextIndex >= previousIndex ? 1 : -1;

            if (activeSection && activeSection !== section) {
                activeSection.classList.remove("is-story-active");
                hideSectionText(activeSection, direction);
            }

            section.classList.add("is-story-active");
            revealSectionText(section, direction);
            storyElement.dataset.stage = stage;
            updateTerminal(stage);
            updateDetails(stage);
            playScene(stage);

            const content = stageContent[stage] || stageContent.idea;
            animate(storyElement, {
                "--story-x": `${isCompact ? 50 : content.x}%`,
                "--story-scale": isCompact ? 0.82 : content.scale,
                opacity: [0.76, 1],
                duration: 980,
                ease: "outExpo"
            });

            animate(storyFrame, {
                opacity: [0.62, 1],
                scale: [0.96, 1],
                rotate: [direction > 0 ? -0.6 : 0.6, 0],
                duration: 820,
                ease: "outExpo"
            });

            activeSection = section;
            activeStage = stage;
        };

        cleanupCallbacks.push(()=>textAnimations.forEach(animation=>animation.pause()));
        buildTextRecords();
        setTerminalStatic("idea");

        const orbits = storyElement.querySelectorAll("[data-story-orbit]");
        const signal = storyElement.querySelector("[data-story-signal]");

        animate(orbits[0], {
            rotate: "1turn",
            duration: 22000,
            loop: true,
            ease: "linear"
        });

        animate(orbits[1], {
            rotate: "-1turn",
            duration: 16000,
            loop: true,
            ease: "linear"
        });

        animate(signal, {
            strokeDashoffset: [0, -72],
            duration: 2600,
            loop: true,
            ease: "linear"
        });

        let boundaryFrame = 0;
        updateStoryBoundary = () => {
            const stopTop = storyStop ? storyStop.getBoundingClientRect().top : Number.POSITIVE_INFINITY;
            const breakActive = storyBreaks.some((section) => {
                const bounds = section.getBoundingClientRect();
                return bounds.top <= window.innerHeight * 0.72 && bounds.bottom >= window.innerHeight * 0.28;
            });
            const shouldHide = !storyFocusActive && (isCompact || stopTop <= window.innerHeight * 0.72 || breakActive);
            storyElement.classList.toggle("is-story-hidden", shouldHide);
            const slotBounds=mobileSlot?.getBoundingClientRect();
            const offscreen=isCompact && !storyFocusActive && (!slotBounds || slotBounds.bottom<0 || slotBounds.top>window.innerHeight);
            if (shouldHide || offscreen) {printer?.pause();sceneTimeline?.pause();}
            else {sceneTimeline?.play();if(activeStage==='print') printer?.resume();}
        };

        const scheduleStoryBoundary = () => {
            if (boundaryFrame) return;
            boundaryFrame = requestAnimationFrame(() => {
                boundaryFrame = 0;
                updateStoryBoundary();
            });
        };

        window.addEventListener("scroll", scheduleStoryBoundary, { passive: true });
        window.addEventListener("resize", scheduleStoryBoundary, { passive: true });
        cleanupCallbacks.push(() => {
            window.removeEventListener("scroll", scheduleStoryBoundary);
            window.removeEventListener("resize", scheduleStoryBoundary);
            if (boundaryFrame) cancelAnimationFrame(boundaryFrame);
        });

        if ("IntersectionObserver" in window) {
            const sectionObserver = new IntersectionObserver((entries) => {
                const candidates = entries
                    .filter((entry) => entry.isIntersecting)
                    .sort((a, b) => {
                        const viewportCenter = window.innerHeight / 2;
                        const aCenter = a.boundingClientRect.top + a.boundingClientRect.height / 2;
                        const bCenter = b.boundingClientRect.top + b.boundingClientRect.height / 2;
                        return Math.abs(aCenter - viewportCenter) - Math.abs(bCenter - viewportCenter);
                    });

                if (candidates[0]) activateSection(candidates[0].target);
            }, {
                rootMargin: "-38% 0px -38% 0px",
                threshold: 0
            });

            sections.forEach((section) => sectionObserver.observe(section));
            cleanupCallbacks.push(() => sectionObserver.disconnect());
        } else {
            activateSection(sections[0]);
        }

        requestAnimationFrame(() => {
            const viewportCenter = window.innerHeight / 2;
            const nearest = sections
                .map((section) => {
                    const rect = section.getBoundingClientRect();
                    return {
                        section,
                        distance: Math.abs(rect.top + rect.height / 2 - viewportCenter)
                    };
                })
                .sort((a, b) => a.distance - b.distance)[0];

            activateSection(nearest?.section || sections[0]);
            updateStoryBoundary();
        });

        document.documentElement.dataset.storyAnimations = "ready";

        return () => cleanupCallbacks.forEach((callback) => callback());
    });

    window.addEventListener("pagehide", () => {
        storyScope.revert();
        globalCleanupCallbacks.forEach((callback) => callback());
    }, { once: true });
}
