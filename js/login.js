      /* ============================================
         تسجيل دخول حقيقي: بيبعت اسم المستخدم وكلمة السر
         للسيرفر (POST /api/login)، والسيرفر يتحقق منهم
         بقاعدة البيانات (كلمة السر مخزّنة مشفّرة، مو نص عادي)
         وبيرجع session cookie آمن.
      ============================================ */
      const loginForm = document.getElementById("loginForm");
      const errorMsg = document.getElementById("errorMsg");
      const submitBtn = loginForm.querySelector(".login-btn");

      loginForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        errorMsg.classList.remove("show");

        const username = document.getElementById("username").value.trim();
        const password = document.getElementById("password").value;

        submitBtn.disabled = true;
        submitBtn.textContent = "جاري الدخول...";

        try {
          const res = await fetch("/api/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password }),
          });
          const data = await res.json();

          if (res.ok && data.success) {
            window.location.href = "Dashboard.html";
            return;
          }

          errorMsg.textContent = data.error || "اسم المستخدم أو كلمة السر غلط.";
          errorMsg.classList.add("show");
        } catch (err) {
          errorMsg.textContent = "صار خطأ بالاتصال بالسيرفر. حاولي كمان مرة.";
          errorMsg.classList.add("show");
        } finally {
          submitBtn.disabled = false;
          submitBtn.textContent = "دخول";
        }
      });
