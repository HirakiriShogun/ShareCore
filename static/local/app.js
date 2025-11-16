(function () {
    // Общие утилиты для локального админа

    // Visual viewport height fix для мобильных
    const page = document.querySelector('.local-page');
    if (page) {
        const vvh = () => {
            const vh = window.visualViewport
                ? window.visualViewport.height
                : window.innerHeight;
            page.style.minHeight = vh + 'px';
        };

        vvh();
        window.addEventListener('resize', vvh);
        if (window.visualViewport) {
            window.visualViewport.addEventListener('resize', vvh);
        }
    }

    // Parallax эффект для десктопа
    const prefersReduced = window.matchMedia &&
        window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const supportsFinePointer = window.matchMedia('(pointer:fine)').matches;

    if (!prefersReduced && supportsFinePointer) {
        const blobA = document.querySelector('.bg-blob-a');
        const blobB = document.querySelector('.bg-blob-b');

        if (blobA || blobB) {
            let rafId = null;
            window.addEventListener('mousemove', (e) => {
                if (rafId) cancelAnimationFrame(rafId);

                rafId = requestAnimationFrame(() => {
                    const x = (e.clientX / window.innerWidth - 0.5) * 20;
                    const y = (e.clientY / window.innerHeight - 0.5) * 20;

                    if (blobA) {
                        blobA.style.transform = `translate3d(${x}px, ${y}px, 0)`;
                    }
                    if (blobB) {
                        blobB.style.transform = `translate3d(${-x}px, ${-y}px, 0)`;
                    }
                });
            }, { passive: true });
        }
    }
})();
