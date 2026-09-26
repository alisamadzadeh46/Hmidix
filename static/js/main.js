// Hamidix front-end helpers
(function () {
    function getCookie(name) {
        const m = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
        return m ? m.pop() : '';
    }
    function csrfToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        return getCookie('csrftoken') || (meta ? meta.content : '');
    }

    // ─── Auto-dismiss messages ───────────────────────────────
    document.querySelectorAll('.messages .msg').forEach(function (msg) {
        setTimeout(function () {
            msg.style.transition = 'opacity .5s, max-height .5s, margin .5s, padding .5s';
            msg.style.opacity = '0';
            msg.style.maxHeight = '0';
            msg.style.marginBottom = '0';
            msg.style.paddingTop = '0';
            msg.style.paddingBottom = '0';
            setTimeout(function () { msg.remove(); }, 520);
        }, 4000);
    });

    // ─── AJAX add-to-cart ────────────────────────────────────
    document.querySelectorAll('.add-to-cart[data-add-url]').forEach(function (btn) {
        btn.addEventListener('click', function () {
            const url = btn.dataset.addUrl;
            const original = btn.innerHTML;
            fetch(url, {
                method: 'POST',
                headers: { 'X-Requested-With': 'XMLHttpRequest', 'X-CSRFToken': csrfToken() },
            })
            .then(function (r) {
                return r.json().then(function (data) {
                    if (!r.ok) throw new Error(data.error || 'request failed');
                    return data;
                });
            })
            .then(function (data) {
                const counter = document.getElementById('cartCount');
                if (counter && typeof data.count !== 'undefined') counter.textContent = data.count;
                btn.innerHTML = '<i class="fas fa-check"></i> افزوده شد';
                btn.style.background = 'var(--success)';
                setTimeout(function () { btn.innerHTML = original; btn.style.background = ''; }, 1600);
            })
            .catch(function () {
                btn.innerHTML = 'خطا، دوباره تلاش کنید';
                setTimeout(function () { btn.innerHTML = original; }, 1600);
            });
        });
    });

    // ─── Quantity stepper ────────────────────────────────────
    document.querySelectorAll('.qty-control').forEach(function (ctrl) {
        const input = ctrl.querySelector('input');
        const max = parseInt(input.getAttribute('max'), 10) || Infinity;
        const min = parseInt(input.getAttribute('min'), 10) || 1;
        const form = ctrl.closest('.cart-qty-form');
        function changed() { if (form) form.submit(); }
        ctrl.querySelector('.qty-plus').addEventListener('click', function () {
            const v = parseInt(input.value, 10) || min;
            if (v < max) { input.value = v + 1; changed(); }
        });
        ctrl.querySelector('.qty-minus').addEventListener('click', function () {
            const v = parseInt(input.value, 10) || min;
            if (v > min) { input.value = v - 1; changed(); }
        });
    });

    // ─── Hero slider ─────────────────────────────────────────
    const slider = document.getElementById('heroSlider');
    if (slider) {
        const slides = slider.querySelectorAll('.slide');
        const dots = slider.querySelectorAll('.dot');
        let index = 0, timer = null;
        function show(i) {
            index = (i + slides.length) % slides.length;
            slides.forEach(function (s, n) { s.classList.toggle('active', n === index); });
            dots.forEach(function (d, n) { d.classList.toggle('active', n === index); });
        }
        function next() { show(index + 1); }
        function prev() { show(index - 1); }
        function start() { if (slides.length > 1) timer = setInterval(next, 5000); }
        function reset() { clearInterval(timer); start(); }
        const nextBtn = slider.querySelector('.slider-btn.next');
        const prevBtn = slider.querySelector('.slider-btn.prev');
        if (nextBtn) nextBtn.addEventListener('click', function () { next(); reset(); });
        if (prevBtn) prevBtn.addEventListener('click', function () { prev(); reset(); });
        dots.forEach(function (d) {
            d.addEventListener('click', function () { show(parseInt(d.dataset.index, 10)); reset(); });
        });

        // Swipe support for touch screens (arrows are hidden on phones).
        const rtl = getComputedStyle(slider).direction === 'rtl';
        let touchX = null;
        slider.addEventListener('touchstart', function (e) { touchX = e.touches[0].clientX; }, { passive: true });
        slider.addEventListener('touchend', function (e) {
            if (touchX === null) return;
            const dx = e.changedTouches[0].clientX - touchX;
            touchX = null;
            if (Math.abs(dx) < 40) return;
            // In a right-to-left layout the next slide comes from the left.
            if ((dx > 0) === rtl) next(); else prev();
            reset();
        });
        start();
    }

    // ─── Product row arrows ───────────────────────────────────
    document.querySelectorAll('.row-wrap').forEach(function (wrap) {
        const row = wrap.querySelector('.products-row');
        const nextBtn = wrap.querySelector('.row-next');
        const prevBtn = wrap.querySelector('.row-prev');
        const step = 224;
        function updateArrows() {
            if (nextBtn) nextBtn.style.opacity = (row.scrollLeft > -(row.scrollWidth - row.clientWidth - 10)) ? '1' : '0.3';
            if (prevBtn) prevBtn.style.opacity = (row.scrollLeft < -10) ? '1' : '0.3';
        }
        if (nextBtn) nextBtn.addEventListener('click', function () { row.scrollBy({ left: -step * 2, behavior: 'smooth' }); });
        if (prevBtn) prevBtn.addEventListener('click', function () { row.scrollBy({ left: step * 2, behavior: 'smooth' }); });
        row.addEventListener('scroll', updateArrows);
        updateArrows();
    });

    // ─── Product Gallery ──────────────────────────────────────
    var mainImg  = document.getElementById('galleryMainImg');
    var mainBox  = document.getElementById('galleryMain');
    var thumbs   = document.querySelectorAll('.gallery-thumb');
    var counter  = document.getElementById('galleryCounter');
    var gNext    = document.getElementById('gNext');
    var gPrev    = document.getElementById('gPrev');
    var lightbox = document.getElementById('lightbox');
    var lbImg    = document.getElementById('lightboxImg');
    var lbClose  = document.getElementById('lightboxClose');
    var lbNext   = document.getElementById('lbNext');
    var lbPrev   = document.getElementById('lbPrev');

    var gallerySrcs = [];
    thumbs.forEach(function (t) { gallerySrcs.push(t.dataset.src); });
    var lbIndex = 0;

    function setThumb(idx) {
        idx = (idx + gallerySrcs.length) % gallerySrcs.length;
        thumbs.forEach(function (t, i) { t.classList.toggle('active', i === idx); });
        if (mainImg && gallerySrcs[idx]) mainImg.src = gallerySrcs[idx];
        if (counter) counter.textContent = (idx + 1) + ' / ' + gallerySrcs.length;
        // scroll active thumb into view
        if (thumbs[idx]) thumbs[idx].scrollIntoView({ block: 'nearest', inline: 'nearest' });
        lbIndex = idx;
    }

    thumbs.forEach(function (thumb, idx) {
        thumb.addEventListener('click', function () { setThumb(idx); });
    });

    // Prev / Next nav arrows
    if (gNext) gNext.addEventListener('click', function (e) { e.stopPropagation(); setThumb(lbIndex + 1); });
    if (gPrev) gPrev.addEventListener('click', function (e) { e.stopPropagation(); setThumb(lbIndex - 1); });

    // Zoom on hover — track cursor position
    if (mainBox && mainImg) {
        mainBox.addEventListener('mousemove', function (e) {
            var rect = mainBox.getBoundingClientRect();
            var x = ((e.clientX - rect.left) / rect.width * 100).toFixed(1) + '%';
            var y = ((e.clientY - rect.top) / rect.height * 100).toFixed(1) + '%';
            mainBox.style.setProperty('--zoom-x', x);
            mainBox.style.setProperty('--zoom-y', y);
            mainBox.classList.add('zooming');
        });
        mainBox.addEventListener('mouseleave', function () {
            mainBox.classList.remove('zooming');
        });
    }

    // Lightbox open on main image click
    if (mainBox && lightbox) {
        mainBox.addEventListener('click', function () {
            lbImg.src = mainImg.src;
            lightbox.classList.add('open');
        });
        lbClose && lbClose.addEventListener('click', function () { lightbox.classList.remove('open'); });
        lightbox.addEventListener('click', function (e) { if (e.target === lightbox) lightbox.classList.remove('open'); });
        document.addEventListener('keydown', function (e) {
            if (!lightbox.classList.contains('open')) return;
            if (e.key === 'Escape') lightbox.classList.remove('open');
            if (e.key === 'ArrowRight') { setThumb(lbIndex - 1); lbImg.src = gallerySrcs[lbIndex]; }
            if (e.key === 'ArrowLeft')  { setThumb(lbIndex + 1); lbImg.src = gallerySrcs[lbIndex]; }
        });
        lbNext && lbNext.addEventListener('click', function () {
            setThumb(lbIndex - 1); lbImg.src = gallerySrcs[lbIndex];
        });
        lbPrev && lbPrev.addEventListener('click', function () {
            setThumb(lbIndex + 1); lbImg.src = gallerySrcs[lbIndex];
        });
    }
})();
