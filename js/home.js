/* ============================================
         1) عداد مزاد اللحظة بالصفحة الرئيسية
         نفس منطق صفحة المزادات: target = الآن + عدد ثواني ثابت
      ============================================ */
      const TEASER_ENDS_IN_SECONDS = 2400; // 40 دقيقة (نفس مزاد Lot 04 بصفحة المزادات)
      const teaserTarget = Date.now() + TEASER_ENDS_IN_SECONDS * 1000;

      function pad(n) {
        return String(n).padStart(2, "0");
      }

      function tickTeaser() {
        const remaining = teaserTarget - Date.now();
        const totalSeconds = Math.max(0, Math.floor(remaining / 1000));
        const d = Math.floor(totalSeconds / 86400);
        const h = Math.floor((totalSeconds % 86400) / 3600);
        const m = Math.floor((totalSeconds % 3600) / 60);
        const s = totalSeconds % 60;

        document.querySelector(".td").textContent = d;
        document.querySelector(".th").textContent = pad(h);
        document.querySelector(".tm").textContent = pad(m);
        document.querySelector(".ts").textContent = pad(s);
      }

      tickTeaser();
      setInterval(tickTeaser, 1000);
/* ============================================
         2) Fade-in عند التمرير (Intersection Observer)
      ============================================ */
      const revealEls = document.querySelectorAll(".reveal");
      const observer = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (entry.isIntersecting) {
              entry.target.classList.add("in-view");
              observer.unobserve(entry.target);
            }
          });
        },
        { threshold: 0.15 }
      );
      revealEls.forEach((el) => observer.observe(el));
