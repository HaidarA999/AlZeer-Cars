/* ============================================
         عناصر أساسية
      ============================================ */
      const grid = document.getElementById("carsGrid");
      const cards = Array.from(grid.querySelectorAll(".car-card"));
      const resultCount = document.getElementById("resultCount");
      const noResults = document.getElementById("noResults");
      const chips = document.querySelectorAll(".chip");
      const searchInput = document.getElementById("searchInput");
      const sortSelect = document.getElementById("sortSelect");

      let activeFilter = "all";
/* ============================================
         1) الفلترة + البحث الحي
         بنفلتر حسب نوع الوقود (activeFilter) وحسب كلمة البحث سوا
      ============================================ */
      function applyFilters() {
        const query = searchInput.value.trim().toLowerCase();
        let visibleCount = 0;

        cards.forEach((card) => {
          const matchesFilter =
            activeFilter === "all" || card.dataset.fuel === activeFilter;
          const matchesSearch = card.dataset.name
            .toLowerCase()
            .includes(query);

          const isVisible = matchesFilter && matchesSearch;
          card.style.display = isVisible ? "" : "none";
          if (isVisible) visibleCount++;
        });

        resultCount.textContent = visibleCount;
        noResults.classList.toggle("show", visibleCount === 0);
      }

      // كبسة على شريحة فلتر (chip)
      chips.forEach((chip) => {
        chip.addEventListener("click", () => {
          chips.forEach((c) => c.classList.remove("active"));
          chip.classList.add("active");
          activeFilter = chip.dataset.filter;
          applyFilters();
        });
      });

      // البحث بيشتغل مع كل حرف يكتبه المستخدم
      searchInput.addEventListener("input", applyFilters);
/* ============================================
         2) الترتيب حسب السعر
         بنرتب عناصر الـDOM نفسها وبنعيد إدراجها بالـgrid
      ============================================ */
      sortSelect.addEventListener("change", () => {
        const value = sortSelect.value;
        let sorted = [...cards];

        if (value === "asc") {
          sorted.sort((a, b) => a.dataset.price - b.dataset.price);
        } else if (value === "desc") {
          sorted.sort((a, b) => b.dataset.price - a.dataset.price);
        }
        // "default" = نرجع للترتيب الأصلي زي ما كانوا بالـHTML
        else {
          sorted = cards;
        }

        sorted.forEach((card) => grid.appendChild(card));
      });
/* ============================================
         3) زر المفضلة (♥) — toggle بسيط
      ============================================ */
      document.querySelectorAll(".fav-btn").forEach((btn) => {
        btn.addEventListener("click", (e) => {
          e.stopPropagation(); // حتى ما تفتح المودال لما تدوس على القلب
          btn.classList.toggle("active");
        });
      });
/* ============================================
         4) Quick View Modal
      ============================================ */
      const overlay = document.getElementById("modalOverlay");
      const modalImg = document.getElementById("modalImg");
      const modalThumbs = document.getElementById("modalThumbs");
      const galleryCounter = document.getElementById("galleryCounter");
      const galleryPrev = document.getElementById("galleryPrev");
      const galleryNext = document.getElementById("galleryNext");

      let currentImages = [];
      let currentIndex = 0;
/* ============================================
         4.1) معرض الصور جوا المودال
         بنقرأ data-images (مفصولة بفواصل)، ولو ما في نرجع لصورة data-img لحالها
      ============================================ */
      function setGalleryImage(index) {
        if (!currentImages.length) return;
        currentIndex = (index + currentImages.length) % currentImages.length;
        modalImg.src = currentImages[currentIndex];
        galleryCounter.textContent = `${currentIndex + 1} / ${currentImages.length}`;

        modalThumbs.querySelectorAll("button").forEach((btn, i) => {
          btn.classList.toggle("active", i === currentIndex);
        });
      }

      function buildGallery(card) {
        const imagesAttr = card.dataset.images;
        currentImages = imagesAttr
          ? imagesAttr.split(",").map((src) => src.trim()).filter(Boolean)
          : [card.dataset.img];

        modalThumbs.innerHTML = "";

        // لو صورة وحدة بس، منخبي الأسهم والعداد ومنعرض صورة وحدة بدون thumbnails
        const multiImages = currentImages.length > 1;
        galleryPrev.style.display = multiImages ? "flex" : "none";
        galleryNext.style.display = multiImages ? "flex" : "none";
        galleryCounter.style.display = multiImages ? "block" : "none";
        modalThumbs.style.display = multiImages ? "flex" : "none";

        currentImages.forEach((src, i) => {
          const thumb = document.createElement("button");
          thumb.type = "button";
          thumb.setAttribute("aria-label", `صورة ${i + 1}`);
          const thumbImg = document.createElement("img");
          thumbImg.src = src;
          thumbImg.alt = "";
          thumb.appendChild(thumbImg);
          thumb.addEventListener("click", () => setGalleryImage(i));
          modalThumbs.appendChild(thumb);
        });

        setGalleryImage(0);
      }

      galleryPrev.addEventListener("click", () => setGalleryImage(currentIndex - 1));
      galleryNext.addEventListener("click", () => setGalleryImage(currentIndex + 1));

      function openModal(card) {
        buildGallery(card);
        modalImg.alt = card.dataset.name;
        document.getElementById("modalName").textContent = card.dataset.name;
        document.getElementById("modalYear").textContent = card.dataset.year;
        document.getElementById("modalCondition").textContent =
          card.dataset.condition;
        document.getElementById("modalGear").textContent = card.dataset.gear;
        document.getElementById("modalFuel").textContent = card.dataset.fuel;
        document.getElementById("modalKm").textContent = card.dataset.km;
        document.getElementById("modalDesc").textContent =
          card.dataset.desc || "";
        document.getElementById("modalPrice").textContent =
          "$" + Number(card.dataset.price).toLocaleString("en-US");

        overlay.classList.add("open");
        document.body.style.overflow = "hidden"; // منع سكرول الخلفية والمودال مفتوح
      }

      function closeModal() {
        overlay.classList.remove("open");
        document.body.style.overflow = "";
      }

      cards.forEach((card) => {
        const btn = card.querySelector(".details-btn");
        btn.addEventListener("click", () => openModal(card));
      });

      document.getElementById("modalClose").addEventListener("click", closeModal);

      // إغلاق لما تدوس برا صندوق المودال
      overlay.addEventListener("click", (e) => {
        if (e.target === overlay) closeModal();
      });

      // إغلاق بزر Escape (مهم لسهولة الوصول)
      document.addEventListener("keydown", (e) => {
        if (!overlay.classList.contains("open")) return;
        if (e.key === "Escape") closeModal();
        if (e.key === "ArrowLeft") setGalleryImage(currentIndex - 1);
        if (e.key === "ArrowRight") setGalleryImage(currentIndex + 1);
      });

      // أول تحميل: تأكد إن العداد صحيح
      applyFilters();
