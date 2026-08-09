(function () {
  var frame = document.getElementById('heroFrame');
  if (!frame) return;

  var slides = frame.querySelectorAll('.frame-slide');
  if (slides.length < 2) return; // only one photo — nothing to rotate/control

  var dotsWrap = document.getElementById('frameDots');
  var dots = dotsWrap ? dotsWrap.querySelectorAll('.frame-dot') : [];
  var prevBtn = document.getElementById('framePrev');
  var nextBtn = document.getElementById('frameNext');

  var index = 0;
  var AUTO_MS = 4500;
  var timer = null;

  function show(target) {
    slides[index].classList.remove('active');
    if (dots[index]) dots[index].classList.remove('active');

    index = (target + slides.length) % slides.length;

    slides[index].classList.add('active');
    if (dots[index]) dots[index].classList.add('active');
  }

  function next() { show(index + 1); }
  function prev() { show(index - 1); }

  function startAuto() {
    stopAuto();
    timer = setInterval(next, AUTO_MS);
  }
  function stopAuto() {
    if (timer) clearInterval(timer);
  }
  // manual interaction resets the auto-shuffle timer so it doesn't jump
  // again right after someone has just picked a slide
  function afterManualAction() {
    startAuto();
  }

  if (nextBtn) nextBtn.addEventListener('click', function () { next(); afterManualAction(); });
  if (prevBtn) prevBtn.addEventListener('click', function () { prev(); afterManualAction(); });

  dots.forEach(function (dot, i) {
    dot.addEventListener('click', function () { show(i); afterManualAction(); });
  });

  // swipe support on touch devices
  var touchStartX = 0;
  frame.addEventListener('touchstart', function (e) {
    touchStartX = e.touches[0].clientX;
  }, { passive: true });

  frame.addEventListener('touchend', function (e) {
    var diff = e.changedTouches[0].clientX - touchStartX;
    if (Math.abs(diff) > 40) {
      if (diff < 0) { next(); } else { prev(); }
      afterManualAction();
    }
  }, { passive: true });

  startAuto();
})();