/* Listing works independently of the optional animation module. */
(function () {
  'use strict';
  var section = document.getElementById('opiniones');
  if (!section) return;
  var cards = Array.from(section.querySelectorAll('[data-review-card]'));
  var filters = Array.from(section.querySelectorAll('[data-review-filter]'));
  var more = section.querySelector('[data-review-more]');
  var kind = 'all', expanded = false;
  function update() {
    var matched = cards.filter(function(card) { return kind === 'all' || card.dataset.reviewKind === kind; });
    cards.forEach(function(card) { var index = matched.indexOf(card); card.hidden = index < 0 || (!expanded && index >= 5); });
    var shown = expanded ? matched.length : Math.min(5, matched.length);
    section.querySelector('[data-review-count]').textContent = 'Mostrando ' + shown + ' de ' + matched.length + ' opiniones';
    section.querySelector('[data-review-filter-empty]').hidden = matched.length !== 0;
    section.querySelector('[data-review-filter-status]').textContent = shown + ' de ' + matched.length + ' experiencias visibles.';
    more.hidden = matched.length <= 5;
    more.textContent = expanded ? 'Ver menos opiniones' : 'Ver más opiniones (' + (matched.length - shown) + ')';
    more.setAttribute('aria-expanded', String(expanded));
    filters.forEach(function(button) { button.setAttribute('aria-pressed', String(button.dataset.reviewFilter === kind)); });
  }
  filters.forEach(function(button) { button.addEventListener('click', function() { kind = button.dataset.reviewFilter; expanded = false; update(); }); });
  more.addEventListener('click', function() { expanded = !expanded; update(); if (!expanded) section.querySelector('.reviews-toolbar').scrollIntoView({block:'start'}); });
  section.querySelector('.reviews-filters').hidden = false;
  update();
})();
