      /* ============================================
         0) بيانات تجريبية (بديل مؤقت لحد ما يصير عندك API حقيقي)
         منخزنها هون بذاكرة الصفحة بس — أي refresh بيرجعها لأصلها
      ============================================ */
      let cars = [
        { id: "c1", name: "فورد موستنج GT 2023", year: 2023, price: 27500, km: 8200, status: "available", img: "images/Cars/car1.jpg" },
        { id: "c2", name: "أودي A8 2022", year: 2022, price: 41000, km: 12500, status: "available", img: "images/Cars/car2.jpg" },
        { id: "c3", name: "بورشه باناميرا 2022", year: 2022, price: 68000, km: 15400, status: "reserved", img: "images/Cars/car3.jpg" },
        { id: "c4", name: "تسلا موديل S 2023", year: 2023, price: 54000, km: 4100, status: "available", img: "images/Cars/car4.jpg" },
        { id: "c5", name: "تويوتا كامري هايبرد 2023", year: 2023, price: 24500, km: 9800, status: "sold", img: "images/Cars/car5.jpg" },
        { id: "c6", name: "بي ام دبليو الفئة 5 2022", year: 2022, price: 31200, km: 21000, status: "available", img: "images/Cars/car6.jpg" },
        { id: "c7", name: "أودي R8 2021", year: 2021, price: 91500, km: 18700, status: "available", img: "images/Cars/car7.jpg" },
        { id: "c8", name: "كيا سبورتاج 2022", year: 2022, price: 21900, km: 32500, status: "available", img: "images/Cars/car8.jpg" },
        { id: "c9", name: "مرسيدس EQS 2023", year: 2023, price: 76300, km: 6900, status: "reserved", img: "images/Cars/car9.jpg" },
      ];

      let auctions = [
        { id: "a1", name: "فورد موستنج GT 2023", currentBid: 27500, minIncrement: 500, bidCount: 14, endsAt: Date.now() + 20400 * 1000, img: "images/Cars/car1.jpg" },
        { id: "a2", name: "بورشه باناميرا 2022", currentBid: 68000, minIncrement: 1000, bidCount: 22, endsAt: Date.now() + 97200 * 1000, img: "images/Cars/car3.jpg" },
        { id: "a3", name: "تسلا موديل S 2023", currentBid: 54000, minIncrement: 750, bidCount: 9, endsAt: Date.now() + 226800 * 1000, img: "images/Cars/car4.jpg" },
        { id: "a4", name: "بي ام دبليو الفئة 5 2022", currentBid: 31200, minIncrement: 500, bidCount: 31, endsAt: Date.now() + 2400 * 1000, img: "images/Cars/car6.jpg" },
        { id: "a5", name: "أودي R8 2021", currentBid: 91500, minIncrement: 1500, bidCount: 17, endsAt: Date.now() + 367200 * 1000, img: "images/Cars/car7.jpg" },
        { id: "a6", name: "مرسيدس EQS 2023", currentBid: 76300, minIncrement: 1000, bidCount: 12, endsAt: Date.now() + 43200 * 1000, img: "images/Cars/car9.jpg" },
      ];

      let editingCarId = null;
      let editingAuctionId = null;

      /* ============================================
         1) التنقل بين الأقسام (Sidebar)
      ============================================ */
      const navButtons = document.querySelectorAll(".nav-item");
      const views = document.querySelectorAll(".view");
      const pageTitle = document.getElementById("pageTitle");
      const titles = { overview: "نظرة عامة", cars: "إدارة السيارات", auctions: "إدارة المزادات" };

      function switchView(viewName) {
        views.forEach((v) => v.classList.toggle("active", v.id === "view-" + viewName));
        navButtons.forEach((b) => b.classList.toggle("active", b.dataset.view === viewName));
        pageTitle.textContent = titles[viewName];
        closeSidebar();
      }

      navButtons.forEach((btn) => {
        btn.addEventListener("click", () => switchView(btn.dataset.view));
      });

      /* ============================================
         2) قائمة الموبايل (Sidebar off-canvas)
      ============================================ */
      const sidebar = document.getElementById("sidebar");
      const sidebarOverlay = document.getElementById("sidebarOverlay");
      const menuBtn = document.getElementById("menuBtn");

      function openSidebar() {
        sidebar.classList.add("open");
        sidebarOverlay.classList.add("show");
      }
      function closeSidebar() {
        sidebar.classList.remove("open");
        sidebarOverlay.classList.remove("show");
      }
      menuBtn.addEventListener("click", openSidebar);
      sidebarOverlay.addEventListener("click", closeSidebar);

      /* ============================================
         3) أدوات مساعدة
      ============================================ */
      function fmt(n) {
        return Number(n).toLocaleString("en-US");
      }

      function pad(n) {
        return String(n).padStart(2, "0");
      }

      function timeLeftLabel(endsAt) {
        const remaining = endsAt - Date.now();
        if (remaining <= 0) return { text: "انتهى", status: "ended" };
        const totalSeconds = Math.floor(remaining / 1000);
        const d = Math.floor(totalSeconds / 86400);
        const h = Math.floor((totalSeconds % 86400) / 3600);
        const m = Math.floor((totalSeconds % 3600) / 60);
        const status = remaining / 1000 < 6 * 3600 ? "ending" : "live";
        let text;
        if (d > 0) text = `${d} يوم ${h} س`;
        else if (h > 0) text = `${h} س ${m} د`;
        else text = `${m} د ${pad(Math.floor(totalSeconds % 60))} ث`;
        return { text, status };
      }

      function showToast(msg) {
        const toast = document.getElementById("toast");
        document.getElementById("toastMsg").textContent = msg;
        toast.classList.add("show");
        clearTimeout(showToast._t);
        showToast._t = setTimeout(() => toast.classList.remove("show"), 2200);
      }

      const carStatusLabel = { available: "متاحة", reserved: "محجوزة", sold: "مباعة" };

      /* ============================================
         4) رسم جدول السيارات
      ============================================ */
      const carsTableBody = document.getElementById("carsTableBody");
      const carSearch = document.getElementById("carSearch");

      function renderCars() {
        const query = carSearch.value.trim().toLowerCase();
        const filtered = cars.filter((c) => c.name.toLowerCase().includes(query));

        if (!filtered.length) {
          carsTableBody.innerHTML = `<tr class="empty-row"><td colspan="4">ما في سيارات مطابقة.</td></tr>`;
          return;
        }

        carsTableBody.innerHTML = filtered
          .map(
            (c) => `
          <tr>
            <td data-label="السيارة">
              <div class="cell-item">
                <img src="${c.img}" alt="${c.name}" onerror="this.style.visibility='hidden'" />
                <div>
                  <strong>${c.name}</strong>
                  <small class="num">${c.year} · ${fmt(c.km || 0)} كم</small>
                </div>
              </div>
            </td>
            <td data-label="السعر"><span class="num">$${fmt(c.price)}</span></td>
            <td data-label="الحالة"><span class="badge ${c.status}">${carStatusLabel[c.status]}</span></td>
            <td data-label="إجراءات">
              <div class="row-actions">
                <button class="icon-btn" aria-label="تعديل" onclick="openCarModal('${c.id}')">
                  <svg viewBox="0 0 24 24" stroke-width="2" fill="none" stroke="currentColor"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path><path d="M18.5 2.5a2.1 2.1 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5Z"></path></svg>
                </button>
                <button class="icon-btn danger" aria-label="حذف" onclick="deleteCar('${c.id}')">
                  <svg viewBox="0 0 24 24" stroke-width="2" fill="none" stroke="currentColor"><path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2m3 0-1 14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2L4 6"></path></svg>
                </button>
              </div>
            </td>
          </tr>`
          )
          .join("");
      }

      carSearch.addEventListener("input", renderCars);

      /* ============================================
         5) رسم جدول المزادات
      ============================================ */
      const auctionsTableBody = document.getElementById("auctionsTableBody");
      const auctionSearch = document.getElementById("auctionSearch");
      const statusLabel = { live: "نشط", ending: "ينتهي قريباً", ended: "منتهي" };

      function renderAuctions() {
        const query = auctionSearch.value.trim().toLowerCase();
        const filtered = auctions.filter((a) => a.name.toLowerCase().includes(query));

        if (!filtered.length) {
          auctionsTableBody.innerHTML = `<tr class="empty-row"><td colspan="5">ما في مزادات مطابقة.</td></tr>`;
          return;
        }

        auctionsTableBody.innerHTML = filtered
          .map((a) => {
            const t = timeLeftLabel(a.endsAt);
            return `
          <tr>
            <td data-label="المزاد">
              <div class="cell-item">
                <img src="${a.img}" alt="${a.name}" onerror="this.style.visibility='hidden'" />
                <div>
                  <strong>${a.name}</strong>
                  <small class="num">${a.bidCount} مزايدة</small>
                </div>
              </div>
            </td>
            <td data-label="أعلى مزايدة"><span class="num">$${fmt(a.currentBid)}</span></td>
            <td data-label="الوقت المتبقي"><span class="num">${t.text}</span></td>
            <td data-label="الحالة"><span class="badge ${t.status}">${statusLabel[t.status]}</span></td>
            <td data-label="إجراءات">
              <div class="row-actions">
                <button class="icon-btn" aria-label="تعديل" onclick="openAuctionModal('${a.id}')">
                  <svg viewBox="0 0 24 24" stroke-width="2" fill="none" stroke="currentColor"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path><path d="M18.5 2.5a2.1 2.1 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5Z"></path></svg>
                </button>
                <button class="icon-btn danger" aria-label="حذف" onclick="deleteAuction('${a.id}')">
                  <svg viewBox="0 0 24 24" stroke-width="2" fill="none" stroke="currentColor"><path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2m3 0-1 14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2L4 6"></path></svg>
                </button>
              </div>
            </td>
          </tr>`;
          })
          .join("");
      }

      auctionSearch.addEventListener("input", renderAuctions);

      /* ============================================
         6) نظرة عامة: إحصائيات + آخر نشاطات
      ============================================ */
      function renderOverview() {
        document.getElementById("statCars").textContent = cars.length;
        document.getElementById("statAuctions").textContent = auctions.filter(
          (a) => a.endsAt > Date.now()
        ).length;
        const bidsTotal = auctions.reduce((sum, a) => sum + a.bidCount, 0);
        document.getElementById("statBids").textContent = bidsTotal;
        const highest = auctions.reduce((max, a) => Math.max(max, a.currentBid), 0);
        document.getElementById("statBidValue").textContent = "$" + fmt(highest);

        const activity = [
          ...cars.slice(-2).map((c) => ({ who: `أضيفت سيارة: ${c.name}`, when: "اليوم" })),
          ...auctions.slice(0, 3).map((a) => ({ who: `مزايدة جديدة على ${a.name}`, when: "قبل قليل" })),
        ];

        document.getElementById("activityList").innerHTML = activity
          .map((item) => `<li><span class="who">${item.who}</span><span class="when">${item.when}</span></li>`)
          .join("");
      }

      /* ============================================
         7) مودال السيارة: فتح / إغلاق / حفظ / حذف
      ============================================ */
      const carModalOverlay = document.getElementById("carModalOverlay");
      const carForm = document.getElementById("carForm");

      window.openCarModal = function (id) {
        editingCarId = id || null;
        const isEdit = !!id;
        document.getElementById("carModalTitle").textContent = isEdit ? "تعديل السيارة" : "إضافة سيارة جديدة";

        if (isEdit) {
          const c = cars.find((x) => x.id === id);
          document.getElementById("carName").value = c.name;
          document.getElementById("carYear").value = c.year;
          document.getElementById("carPrice").value = c.price;
          document.getElementById("carKm").value = c.km;
          document.getElementById("carStatus").value = c.status;
          document.getElementById("carImg").value = c.img;
        } else {
          carForm.reset();
        }
        carModalOverlay.classList.add("open");
      };

      function closeCarModal() {
        carModalOverlay.classList.remove("open");
      }

      document.getElementById("addCarBtn").addEventListener("click", () => openCarModal(null));
      document.getElementById("carModalClose").addEventListener("click", closeCarModal);
      document.getElementById("carCancelBtn").addEventListener("click", closeCarModal);
      carModalOverlay.addEventListener("click", (e) => {
        if (e.target === carModalOverlay) closeCarModal();
      });

      carForm.addEventListener("submit", (e) => {
        e.preventDefault();
        const data = {
          name: document.getElementById("carName").value.trim(),
          year: Number(document.getElementById("carYear").value),
          price: Number(document.getElementById("carPrice").value),
          km: Number(document.getElementById("carKm").value) || 0,
          status: document.getElementById("carStatus").value,
          img: document.getElementById("carImg").value.trim() || "images/Cars/car1.jpg",
        };

        if (editingCarId) {
          const idx = cars.findIndex((c) => c.id === editingCarId);
          cars[idx] = { ...cars[idx], ...data };
          showToast("تم تحديث بيانات السيارة");
        } else {
          cars.push({ id: "c" + Date.now(), ...data });
          showToast("تمت إضافة السيارة بنجاح");
        }

        closeCarModal();
        renderCars();
        renderOverview();
      });

      window.deleteCar = function (id) {
        const car = cars.find((c) => c.id === id);
        if (!confirm(`متأكد إنك بدك تحذف "${car.name}"؟`)) return;
        cars = cars.filter((c) => c.id !== id);
        renderCars();
        renderOverview();
        showToast("تم حذف السيارة");
      };

      /* ============================================
         8) مودال المزاد: فتح / إغلاق / حفظ / حذف
      ============================================ */
      const auctionModalOverlay = document.getElementById("auctionModalOverlay");
      const auctionForm = document.getElementById("auctionForm");

      window.openAuctionModal = function (id) {
        editingAuctionId = id || null;
        const isEdit = !!id;
        document.getElementById("auctionModalTitle").textContent = isEdit ? "تعديل المزاد" : "إضافة مزاد جديد";

        if (isEdit) {
          const a = auctions.find((x) => x.id === id);
          document.getElementById("auctionName").value = a.name;
          document.getElementById("auctionStartPrice").value = a.currentBid;
          document.getElementById("auctionIncrement").value = a.minIncrement;
          const hoursLeft = Math.max(1, Math.round((a.endsAt - Date.now()) / 3600000));
          document.getElementById("auctionDuration").value = hoursLeft;
          document.getElementById("auctionImg").value = a.img;
        } else {
          auctionForm.reset();
        }
        auctionModalOverlay.classList.add("open");
      };

      function closeAuctionModal() {
        auctionModalOverlay.classList.remove("open");
      }

      document.getElementById("addAuctionBtn").addEventListener("click", () => openAuctionModal(null));
      document.getElementById("auctionModalClose").addEventListener("click", closeAuctionModal);
      document.getElementById("auctionCancelBtn").addEventListener("click", closeAuctionModal);
      auctionModalOverlay.addEventListener("click", (e) => {
        if (e.target === auctionModalOverlay) closeAuctionModal();
      });

      auctionForm.addEventListener("submit", (e) => {
        e.preventDefault();
        const hours = Number(document.getElementById("auctionDuration").value);
        const data = {
          name: document.getElementById("auctionName").value.trim(),
          currentBid: Number(document.getElementById("auctionStartPrice").value),
          minIncrement: Number(document.getElementById("auctionIncrement").value),
          endsAt: Date.now() + hours * 3600 * 1000,
          img: document.getElementById("auctionImg").value.trim() || "images/Cars/car1.jpg",
        };

        if (editingAuctionId) {
          const idx = auctions.findIndex((a) => a.id === editingAuctionId);
          auctions[idx] = { ...auctions[idx], ...data };
          showToast("تم تحديث بيانات المزاد");
        } else {
          auctions.push({ id: "a" + Date.now(), bidCount: 0, ...data });
          showToast("تمت إضافة المزاد بنجاح");
        }

        closeAuctionModal();
        renderAuctions();
        renderOverview();
      });

      window.deleteAuction = function (id) {
        const auction = auctions.find((a) => a.id === id);
        if (!confirm(`متأكد إنك بدك تحذف مزاد "${auction.name}"؟`)) return;
        auctions = auctions.filter((a) => a.id !== id);
        renderAuctions();
        renderOverview();
        showToast("تم حذف المزاد");
      };

      /* ============================================
         9) الإطلاق الأولي + تحديث الوقت كل ثانية
      ============================================ */
      renderCars();
      renderAuctions();
      renderOverview();

      setInterval(() => {
        renderAuctions();
        renderOverview();
      }, 1000);
    
