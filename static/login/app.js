(function () {
  const prefersReduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const supportsFinePointer = window.matchMedia('(pointer:fine)').matches;
  const card = document.querySelector('.login-card');
  const email = document.getElementById('email');
  const blobA = document.querySelector('.bg-blob-a');
  const blobB = document.querySelector('.bg-blob-b');

  if (email) {
    setTimeout(() => { try { email.focus({ preventScroll: true }); } catch (_) { } }, 50);
  }

  if (!prefersReduced && card && supportsFinePointer) {
    let rafId = null;
    const onMove = (e) => {
      const rect = card.getBoundingClientRect();
      const cx = rect.left + rect.width / 2;
      const cy = rect.top + rect.height / 2;
      const dx = (e.clientX - cx) / rect.width;
      const dy = (e.clientY - cy) / rect.height;
      if (rafId) cancelAnimationFrame(rafId);
      rafId = requestAnimationFrame(() => {
        const tiltX = (-dy * 1.6).toFixed(2);
        const tiltY = (dx * 2.4).toFixed(2);
        card.style.transform = `perspective(1100px) rotateX(${tiltX}deg) rotateY(${tiltY}deg)`;
        if (blobA) blobA.style.transform = `translate3d(${(dx * 10).toFixed(1)}px, ${(dy * 6).toFixed(1)}px, 0)`;
        if (blobB) blobB.style.transform = `translate3d(${(-dx * 8).toFixed(1)}px, ${(-dy * 5).toFixed(1)}px, 0)`;
      });
    };
    const reset = () => {
      card.style.transform = '';
      if (blobA) blobA.style.transform = '';
      if (blobB) blobB.style.transform = '';
    };
    window.addEventListener('mousemove', onMove, { passive: true });
    window.addEventListener('mouseleave', reset, { passive: true });
  }

  const page = document.querySelector('.login-page');
  const vvh = () => {
    const vh = (window.visualViewport ? window.visualViewport.height : window.innerHeight);
    page && (page.style.minHeight = vh + 'px');
  };
  vvh();
  window.addEventListener('resize', vvh);
  window.visualViewport && window.visualViewport.addEventListener('resize', vvh);

  if (!supportsFinePointer && !prefersReduced) {
    const cardEl = document.querySelector('.login-card');
    const title = document.querySelector('.login-title');
    let t = 0;
    const animate = () => {
      t += 0.012;
      const wobble = Math.sin(t) * 0.4;
      if (cardEl) cardEl.style.transform = `translateY(${wobble}px)`;
      if (title) title.style.textShadow = `0 0 20px rgba(${getComputedStyle(document.documentElement).getPropertyValue('--accent-rgb')}, .25)`;
      requestAnimationFrame(animate);
    };
    requestAnimationFrame(animate);
  }
})();


