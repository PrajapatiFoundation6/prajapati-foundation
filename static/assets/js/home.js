(function () {
  var slides = document.querySelectorAll('.hero-slider .slide');
  if (slides.length < 2) return; // nothing to rotate

  var index = 0;
  setInterval(function () {
    slides[index].classList.remove('active');
    index = (index + 1) % slides.length;
    slides[index].classList.add('active');
  }, 4500);
})();
