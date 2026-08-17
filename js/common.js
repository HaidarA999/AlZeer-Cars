/* ============================================
         0) قائمة الموبايل (Hamburger)
      ============================================ */
      const navToggle = document.getElementById("navToggle");
      const navLinks = document.getElementById("navLinks");

      navToggle.addEventListener("click", () => {
        const isOpen = navLinks.classList.toggle("open");
        navToggle.classList.toggle("open", isOpen);
        navToggle.setAttribute("aria-expanded", isOpen);
      });

      navLinks.querySelectorAll("a").forEach((link) => {
        link.addEventListener("click", () => {
          navLinks.classList.remove("open");
          navToggle.classList.remove("open");
          navToggle.setAttribute("aria-expanded", "false");
        });
      });
