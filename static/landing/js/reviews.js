/* Anime.js is the same local, pinned module used by VillaTech's other scenes. */
import { animate, createTimeline, stagger } from '../vendor/animejs/anime.esm.min.js';

const section = document.getElementById('opiniones');
if (section) {
  const cards = [...section.querySelectorAll('[data-review-card]')];
  const preference = window.matchMedia('(prefers-reduced-motion: reduce)');
  const stage = section.querySelector('.reviews-motion-stage');
  const toggle = section.querySelector('[data-reviews-motion]');
  const counter = section.querySelector('[data-review-counter]');
  const finalScore = counter?.textContent;
  const average = Math.max(0, Math.min(5, Number(section.dataset.average) || 0));
  const number = new Intl.NumberFormat('es-CO', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  const ambient = [];
  const transient = [];
  const observers = [];
  let paused = false, visible = false, disabled = preference.matches;

  section.querySelector('.reviews-filters').hidden = false;
  // Filtering is useful even when animation is disabled.
  for (const button of section.querySelectorAll('[data-review-filter]')) {
    button.addEventListener('click', () => {
      const kind = button.dataset.reviewFilter;
      let shown = 0;
      for (const card of cards) {
        card.hidden = kind !== 'all' && card.dataset.reviewKind !== kind;
        if (!card.hidden) shown++;
      }
      section.querySelectorAll('[data-review-filter]').forEach(item => item.setAttribute('aria-pressed', String(item === button)));
      section.querySelector('[data-review-filter-empty]').hidden = shown !== 0;
      section.querySelector('[data-review-filter-status]').textContent = `${shown} experiencias visibles: ${button.textContent}.`;
    });
  }

  function syncAmbient() {
    const play = visible && !document.hidden && !paused && !disabled;
    for (const animation of ambient) play ? animation.play() : animation.pause();
  }
  function stopMotion() {
    disabled = true;
    observers.forEach(observer => observer.disconnect());
    [...ambient, ...transient].forEach(animation => animation.revert());
    if (counter) counter.textContent = finalScore;
    toggle.hidden = true;
    delete section.dataset.reviewAnimation;
  }
  function revealCards(entries, observer) {
    const targets = entries.filter(entry => entry.isIntersecting && !entry.target.hidden).map(entry => entry.target);
    if (!targets.length || disabled) return;
    targets.forEach(card => observer.unobserve(card));
    transient.push(animate(targets, { opacity: [.65, 1], y: [25, 0], delay: stagger(90), duration: 850, ease: 'outExpo' }));
    for (const card of targets) {
      transient.push(animate(card.querySelectorAll('.review-stars span'), { scale: [.6, 1], rotate: [-18, 0], opacity: [.3, 1], delay: stagger(65, { start: 170 }), duration: 650, ease: 'outBack' }));
    }
  }
  function init() {
    if (disabled || !('IntersectionObserver' in window)) return;
    try {
      section.dataset.reviewAnimation = 'animejs';
      ambient.push(animate(stage.querySelector('.reviews-feedback-bubble'), { y: [-5, 5], rotate: [-1, 1], duration: 3000, alternate: true, loop: true, ease: 'inOutSine', autoplay: false }));
      ambient.push(animate(stage.querySelector('.reviews-verified-bubble'), { y: [4, -4], duration: 2500, alternate: true, loop: true, ease: 'inOutSine', autoplay: false }));
      ambient.push(animate(stage.querySelectorAll('.reviews-spark'), { scale: [.75, 1.15], opacity: [.4, 1], delay: stagger(350), duration: 1500, alternate: true, loop: true, ease: 'inOutSine', autoplay: false }));
      ambient.push(animate(stage.querySelector('.reviews-conversation-path>path'), { strokeDashoffset: [0, -120], duration: 9000, loop: true, ease: 'linear', autoplay: false }));
      const ambientObserver = new IntersectionObserver(entries => { visible = entries[0].isIntersecting; syncAmbient(); }, { threshold: .1 });
      ambientObserver.observe(stage); observers.push(ambientObserver);
      const introObserver = new IntersectionObserver(entries => {
        if (!entries.some(entry => entry.isIntersecting) || disabled) return;
        introObserver.disconnect();
        const timeline = createTimeline({ autoplay: false, defaults: { duration: 1000, ease: 'outExpo' } });
        timeline.add(section.querySelectorAll('[data-review-intro]'), { y: [25, 0], opacity: [.6, 1], delay: stagger(110) }, 0)
          .add(stage.querySelector('.reviews-rating-bubble'), { scale: [.85, 1], rotate: [-7, 0], opacity: [.5, 1] }, 100)
          .add(stage.querySelectorAll('.reviews-scene-stars span'), { scale: [.25, 1], rotate: [-35, 0], delay: stagger(90), ease: 'outBack', duration: 700 }, 500);
        transient.push(timeline); timeline.play();
        if (counter) {
          const score = { value: 0 };
          transient.push(animate(score, { value: average, duration: 1600, ease: 'outExpo', onUpdate: () => { counter.textContent = number.format(score.value); }, onComplete: () => { counter.textContent = finalScore; } }));
        }
      }, { threshold: .12 });
      introObserver.observe(section.querySelector('.customer-reviews-heading')); observers.push(introObserver);
      const cardObserver = new IntersectionObserver(entries => revealCards(entries, cardObserver), { threshold: .08 });
      cards.forEach(card => cardObserver.observe(card)); observers.push(cardObserver);
      toggle.hidden = false;
      toggle.addEventListener('click', () => { paused = !paused; toggle.textContent = paused ? 'Activar animación' : 'Pausar animación'; toggle.setAttribute('aria-pressed', String(paused)); syncAmbient(); });
      document.addEventListener('visibilitychange', syncAmbient);
      preference.addEventListener('change', event => { if (event.matches) stopMotion(); });
    } catch (error) {
      stopMotion(); // Content stays visible even if the animation library fails.
    }
  }
  init();
}
