(function () {
  if (typeof gsap === 'undefined') return; // GSAP failed to load (offline etc.) — fail silently

  var heroTitle = document.querySelector('.hero-content h1, .page-hero h1');
  var heroSub   = document.querySelector('.hero-content .hero-sub, .page-hero p');
  var heroActions = document.querySelector('.hero-actions');

  if (heroTitle) {
    gsap.from(heroTitle, { y: 30, opacity: 0, duration: 0.9, ease: 'power2.out' });
  }
  if (heroSub) {
    gsap.from(heroSub, { y: 24, opacity: 0, duration: 0.9, delay: 0.15, ease: 'power2.out' });
  }
  if (heroActions) {
    gsap.from(heroActions, { y: 20, opacity: 0, duration: 0.9, delay: 0.3, ease: 'power2.out' });
  }

  gsap.from('.navbar', { y: -60, opacity: 0, duration: 0.8, ease: 'power2.out' });
})();
