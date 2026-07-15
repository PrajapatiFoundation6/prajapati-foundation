(function () {
  var navbar = document.getElementById('navbar');
  if (!navbar) return;

  function onScroll() {
    if (window.scrollY > 12) {
      navbar.classList.add('scrolled');
    } else {
      navbar.classList.remove('scrolled');
    }
  }

  onScroll();
  window.addEventListener('scroll', onScroll, { passive: true });
})();
