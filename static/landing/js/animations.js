import { createAdditivePrinter } from "./additive-printer.js";
import {
    animate,
    createScope,
    createTimeline,
    engine,
    onScroll,
    stagger,
    svg,
    utils
} from "../vendor/animejs/anime.esm.min.js";

document.documentElement.dataset.animations = "loading";

const animationRoot = document.querySelector("main");
const animationFailures = [];

if (animationRoot) {
    engine.pauseOnDocumentHidden = true;
    engine.fps = 60;

    const animationScope = createScope({
        root: animationRoot,
        mediaQueries: {
            reduceMotion: "(prefers-reduced-motion: reduce)",
            isSmall: "(max-width: 640px)"
        }
    });

    animationScope.add((scope) => {
        const { reduceMotion, isSmall } = scope.matches;
        const cleanupCallbacks = [];

        const setHeroProgress = (hero, progress) => {
            const layerNumber = hero?.querySelector("[data-layer-number]");
            const safeProgress = Math.min(1, Math.max(0, progress));

            if (layerNumber) {
                layerNumber.textContent = String(Math.round(safeProgress * 68));
            }
        };

        const setLabProgress = (lab, progress) => {
            const safeProgress = Math.min(1, Math.max(0, progress));
            const percentage = Math.round(safeProgress * 100);
            const percentageLabel = lab?.querySelector("[data-print-percent]");
            const track = lab?.querySelector("[data-progress-track]");

            if (percentageLabel) {
                percentageLabel.textContent = `${percentage}%`;
            }

            if (track) {
                track.setAttribute("aria-valuenow", String(percentage));
            }
        };

        const prepareStaticExperience = () => {
            const hero = animationRoot.querySelector("#inicio");
            const lab = animationRoot.querySelector("[data-print-lab]");

            if (hero) {
                const traces = svg.createDrawable(hero.querySelectorAll("[data-print-trace]"));
                traces.forEach((trace) => {
                    trace.draw = "0 1";
                });

                const nozzle = hero.querySelector("[data-printer-nozzle]");
                const progressBar = hero.querySelector("[data-layer-progress]");
                if (nozzle) utils.set(nozzle, { opacity: 0 });
                if (progressBar) utils.set(progressBar, { width: "100%" });
                setHeroProgress(hero, 1);

                const heroStatus = hero.querySelector("[data-print-status]");
                if (heroStatus) heroStatus.textContent = "Modelo listo";
            }

            if (lab) {
                createAdditivePrinter(lab.querySelector("[data-additive-printer]"))?.static();
                const labProgress = lab.querySelector("[data-lab-progress]");
                const labGantry = lab.querySelector("[data-lab-gantry]");
                const labToolhead = lab.querySelector("[data-lab-toolhead]");
                utils.set(lab.querySelectorAll("[data-lab-layer]"), { opacity: 1, scaleX: 1 });
                if (labProgress) utils.set(labProgress, { width: "100%" });
                if (labGantry) utils.set(labGantry, { y: 0 });
                if (labToolhead) utils.set(labToolhead, { x: 0 });
                setLabProgress(lab, 1);

                const labStatus = lab.querySelector("[data-lab-status]");
                const replayButton = lab.querySelector("[data-print-replay]");
                if (labStatus) labStatus.textContent = "Pieza lista";
                if (replayButton) replayButton.disabled = true;
                lab.querySelector("[data-print-console]")?.classList.add("is-complete");
            }
        };

        if (reduceMotion) {
            prepareStaticExperience();
            return () => cleanupCallbacks.forEach((callback) => callback());
        }

        const createHeroExperience = () => {
            const hero = animationRoot.querySelector("#inicio");
            if (!hero) return;

            const brand=hero.querySelector('[data-hero-type]');
            const logo=hero.querySelector('.hero-brand-display');
            const title=hero.querySelector('.hero-title__statement');
            const details=hero.querySelectorAll('.eyebrow,.hero__description,.hero__actions,.hero__trust');
            const original=brand?.textContent || 'VillaTech';
            let typing, intro, visible=false;
            const orbits=Array.from(hero.querySelectorAll('[data-hero-orbit]')).map((element,index)=>animate(element,{rotate:index?'1turn':'-1turn',duration:index?32000:45000,loop:true,ease:'linear',autoplay:false}));
            function enter(){
                if(visible)return;visible=true;
                typing?.pause();intro?.pause();
                orbits.forEach(orbit=>orbit.play());
                intro=createTimeline({defaults:{ease:'outExpo'}})
                    .add(logo,{opacity:[0,1],scale:[.94,1],y:[18,0],duration:1100},0)
                    .add(title,{opacity:[0,1],y:[22,0],filter:['blur(5px)','blur(0px)'],duration:1000},450)
                    .add(details,{opacity:[0,1],y:[12,0],duration:800,delay:stagger(100)},700);
                if(!brand)return;
                brand.setAttribute('aria-label',original);
                const text=document.createElement('span');text.style.display='inline';text.setAttribute('aria-hidden','true');
                const cursor=document.createElement('i');cursor.className='hero-type-cursor';cursor.textContent='▏';cursor.setAttribute('aria-hidden','true');
                brand.replaceChildren(text,cursor);
                const state={letters:0};
                typing=animate(state,{letters:original.length,delay:180,duration:1200,ease:'linear',onUpdate:()=>{text.textContent=original.slice(0,Math.floor(state.letters));},onComplete:()=>{text.textContent=original;cursor.remove();}});
            }
            function leave(){visible=false;typing?.pause();intro?.pause();orbits.forEach(orbit=>orbit.pause());
                // Leave complete readable content when an animation is interrupted.
                if(brand){brand.textContent=original;brand.removeAttribute('aria-label');}
                utils.set([logo,title,...details],{opacity:1,y:0,scale:1,filter:'none'});
            }
            const observer=new IntersectionObserver(entries=>{if(entries[0].isIntersecting)enter();else leave();},{threshold:.1});
            observer.observe(hero);cleanupCallbacks.push(()=>{observer.disconnect();leave();});
        };

        const createPrintLabExperience = () => {
            const lab=animationRoot.querySelector('[data-print-lab]');
            if(!lab)return;
            let percentage=-1;
            const printer=createAdditivePrinter(lab.querySelector('[data-additive-printer]'),progress=>{
                const value=Math.round(progress*100);
                if(value!==percentage){setLabProgress(lab,progress);percentage=value;}
                const bar=lab.querySelector('[data-lab-progress]');if(bar)bar.style.width=`${progress*100}%`;
                lab.querySelector('[data-print-console]')?.classList.toggle('is-complete',progress>=1);
                const status=lab.querySelector('[data-lab-status]');if(status)status.textContent=progress>=1?'Pieza lista':'Imprimiendo por capas';
            });
            if(!printer)return;
            const observer=new IntersectionObserver(entries=>{if(entries[0].isIntersecting)printer.play();else printer.pause();},{threshold:.2});
            observer.observe(lab.querySelector('.print-stage'));
            const replay=()=>printer.play();lab.querySelector('[data-print-replay]')?.addEventListener('click',replay);
            cleanupCallbacks.push(()=>{observer.disconnect();printer.pause();lab.querySelector('[data-print-replay]')?.removeEventListener('click',replay);});
        };

        const createReveal = (containerSelector, itemsSelector, delay = 90) => {
            const container = animationRoot.querySelector(containerSelector);
            const items = container?.querySelectorAll(itemsSelector);

            if (!container || !items?.length) return;

            animate(items, {
                opacity: { from: 0 },
                y: { from: 28 },
                duration: 760,
                delay: stagger(delay),
                ease: "outExpo",
                autoplay: onScroll({
                    target: container,
                    enter: "bottom-=70 top",
                    repeat: true
                }),
                onComplete: utils.cleanInlineStyles
            });
        };

        const createBridgeReveal = () => {
            const bridge = animationRoot.querySelector(".bridge");
            if (!bridge) return;

            const nodes = bridge.querySelectorAll(".bridge__node");
            const dots = bridge.querySelectorAll(".bridge__connection i");
            const bridgeTimeline = createTimeline({
                autoplay: onScroll({
                    target: bridge,
                    enter: "bottom-=80 top",
                    repeat: true
                }),
                onComplete: utils.cleanInlineStyles
            })
                .add(nodes, {
                    opacity: { from: 0 },
                    duration: 720,
                    delay: stagger(150),
                    ease: "outExpo"
                }, 0)
                .add(dots, {
                    opacity: { from: 0 },
                    scale: { from: 0.2 },
                    duration: 520,
                    delay: stagger(85),
                    ease: "outBack(1.8)"
                }, 260);

            bridgeTimeline.init();
        };

        const runExperience = (name, setup) => {
            try {
                setup();
            } catch (error) {
                animationFailures.push(name);
                console.error(`[Landing animations] No se pudo iniciar ${name}.`, error);
            }
        };

        runExperience("hero", createHeroExperience);
        runExperience("laboratorio", createPrintLabExperience);
        runExperience("servicios", () => createReveal("#servicios", ".service-card", 95));
        runExperience("proceso", () => createReveal("#proceso", ".process-step", 110));
        runExperience("proyectos", () => createReveal("#proyectos", ".project-card", 105));
        runExperience("catálogo", () => createReveal("#catalogo", ".product-card", 72));
        runExperience("conexión", createBridgeReveal);

        return () => cleanupCallbacks.forEach((callback) => callback());
    });

    window.addEventListener("pagehide", () => animationScope.revert(), { once: true });
}

document.documentElement.dataset.animations = animationFailures.length ? "partial" : "ready";

if (animationFailures.length) {
    document.documentElement.dataset.animationFailures = animationFailures.join(",");
}

document.dispatchEvent(new CustomEvent("landing:animations-ready", {
    detail: { failures: [...animationFailures] }
}));
