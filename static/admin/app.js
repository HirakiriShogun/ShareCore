(function () {
    const prefersReduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const supportsFinePointer = window.matchMedia('(pointer:fine)').matches;
    const blobA = document.querySelector('.bg-blob-a');
    const blobB = document.querySelector('.bg-blob-b');
    if (!prefersReduced && supportsFinePointer) {
        let rafId = null;
        window.addEventListener('mousemove', (e) => {
            const cx = window.innerWidth / 2; const cy = (window.visualViewport ? window.visualViewport.height : window.innerHeight) / 2;
            const dx = (e.clientX - cx) / window.innerWidth; const dy = (e.clientY - cy) / window.innerHeight;
            if (rafId) cancelAnimationFrame(rafId);
            rafId = requestAnimationFrame(() => {
                if (blobA) blobA.style.transform = `translate3d(${(dx * 10).toFixed(1)}px, ${(dy * 6).toFixed(1)}px, 0)`;
                if (blobB) blobB.style.transform = `translate3d(${(-dx * 8).toFixed(1)}px, ${(-dy * 5).toFixed(1)}px, 0)`;
            });
        }, { passive: true });
    }
})();


