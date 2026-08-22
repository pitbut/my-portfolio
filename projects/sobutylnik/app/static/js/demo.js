(() => {
  const form = document.getElementById("demo-form");
  if (!form) return;
  const input = document.getElementById("demo-input");
  const messages = document.getElementById("demo-messages");
  const turnsLeftEl = document.getElementById("demo-turns-left");
  const cta = document.getElementById("demo-cta");
  const status = document.getElementById("demo-status");

  function addMessage(text, who) {
    const div = document.createElement("div");
    div.className = "msg msg--" + who;
    div.textContent = text;
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
  }

  function lockDemo() {
    input.disabled = true;
    form.querySelector("button").disabled = true;
    status.style.display = "none";
    cta.style.display = "block";
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const text = input.value.trim();
    if (!text) return;
    addMessage(text, "user");
    input.value = "";
    input.disabled = true;

    try {
      const res = await fetch("/demo-reply", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
      });
      const data = await res.json();
      input.disabled = false;
      if (data.error) {
        addMessage("Не получилось ответить — попробуйте ещё раз чуть позже.", "companion");
        return;
      }
      if (data.reply) addMessage(data.reply, "companion");
      if (typeof data.turns_left === "number" && turnsLeftEl) {
        turnsLeftEl.textContent = data.turns_left;
      }
      if (data.limit_reached) lockDemo();
    } catch (err) {
      input.disabled = false;
      addMessage("Ошибка соединения. Попробуйте ещё раз.", "companion");
    }
  });
})();
