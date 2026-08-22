/* Голосовая беседа: распознавание речи (STT), озвучка ответа (TTS) и
 * barge-in — если пользователь начинает говорить, пока собеседник
 * озвучивает ответ, озвучка немедленно прерывается и слушается новая
 * реплика. Использует Web Speech API браузера — доступно в Chrome/Edge
 * (SpeechRecognition только в них, TTS шире). Если API недоступен, работает
 * обычный текстовый чат без микрофона. */
(() => {
  const room = document.getElementById("room");
  if (!room) return;

  const messagesEl = document.getElementById("room-messages");
  const statusEl = document.getElementById("room-status");
  const avatarEl = document.getElementById("avatar-emoji");
  const micBtn = document.getElementById("mic-btn");
  const composerForm = document.getElementById("composer-form");
  const composerInput = document.getElementById("composer-input");
  const voiceSelect = document.getElementById("voice-select");
  const sceneInput = document.getElementById("scene-input");
  let limitReached = room.dataset.limitReached === "true";
  let savedVoiceName = room.dataset.voiceName || "";

  function addMessage(text, who, imageUrl) {
    const div = document.createElement("div");
    div.className = "msg msg--" + who;
    div.textContent = text;
    if (imageUrl) {
      const img = document.createElement("img");
      img.src = imageUrl;
      div.appendChild(img);
    }
    messagesEl.appendChild(div);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function setStatus(text) {
    statusEl.textContent = text;
  }

  function lockRoom(message) {
    limitReached = true;
    document.querySelectorAll("[data-action], #mic-btn, #composer-input, #composer-form button, #scene-input")
      .forEach((el) => (el.disabled = true));
    setStatus(message || "Лимит сообщений исчерпан");
  }

  // --- Text-to-Speech с поддержкой прерывания (barge-in) ---
  let isSpeaking = false;

  function pickVoice() {
    const voices = window.speechSynthesis ? window.speechSynthesis.getVoices() : [];
    if (!voices.length) return null;
    if (savedVoiceName) {
      const match = voices.find((v) => v.name === savedVoiceName);
      if (match) return match;
    }
    return voices.find((v) => v.lang && v.lang.startsWith("ru")) || voices[0];
  }

  function speak(text) {
    if (!window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    const utter = new SpeechSynthesisUtterance(text);
    const voice = pickVoice();
    if (voice) utter.voice = voice;
    utter.lang = voice ? voice.lang : "ru-RU";
    isSpeaking = true;
    avatarEl.classList.add("is-speaking");
    setStatus("Говорит...");
    utter.onend = utter.onerror = () => {
      isSpeaking = false;
      avatarEl.classList.remove("is-speaking");
      setStatus(recognitionActive ? "Слушаю..." : "Готов слушать");
    };
    window.speechSynthesis.speak(utter);
  }

  function populateVoiceOptions() {
    if (!window.speechSynthesis || !voiceSelect) return;
    const voices = window.speechSynthesis.getVoices();
    if (!voices.length) return;
    voiceSelect.innerHTML = "";
    voices.forEach((v) => {
      const opt = document.createElement("option");
      opt.value = v.name;
      opt.textContent = `${v.name} (${v.lang})`;
      if (v.name === savedVoiceName) opt.selected = true;
      voiceSelect.appendChild(opt);
    });
  }
  if (window.speechSynthesis) {
    populateVoiceOptions();
    window.speechSynthesis.onvoiceschanged = populateVoiceOptions;
  }
  if (voiceSelect) {
    voiceSelect.addEventListener("change", () => {
      savedVoiceName = voiceSelect.value;
      fetch("/companion/voice", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ voice_name: savedVoiceName }),
      });
    });
  }

  // --- Отправка реплики/действия на сервер ---
  async function sendTurn(payload) {
    if (limitReached) return;
    try {
      const res = await fetch("/room/message", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (data.limit_reached) {
        lockRoom("Лимит сообщений исчерпан. Загляните в поддержку.");
        return;
      }
      if (data.error) {
        addMessage("Не получилось ответить. Попробуйте ещё раз.", "companion");
        return;
      }
      speak(data.reply);
      addMessage(data.reply, "companion");
    } catch (err) {
      addMessage("Ошибка соединения.", "companion");
    }
  }

  composerForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const text = composerInput.value.trim();
    if (!text) return;
    addMessage(text, "user");
    composerInput.value = "";
    sendTurn({ text });
  });

  document.querySelectorAll("[data-action]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const action = btn.dataset.action;
      const labels = { toast: "🥂 (тост)", joke: "😂 (шутка)", cheers: "🍻 (чокнуться)", music: "🎵 (музыка)" };
      addMessage(labels[action] || action, "user");
      sendTurn({ action });
    });
  });

  if (sceneInput) {
    sceneInput.addEventListener("change", async () => {
      const file = sceneInput.files[0];
      if (!file || limitReached) return;
      const formData = new FormData();
      formData.append("photo", file);
      addMessage("[показываю обстановку]", "user", URL.createObjectURL(file));
      try {
        const res = await fetch("/room/scene", { method: "POST", body: formData });
        const data = await res.json();
        if (data.limit_reached) {
          lockRoom("Лимит сообщений исчерпан. Загляните в поддержку.");
          return;
        }
        if (data.reply) {
          addMessage(data.reply, "companion");
          speak(data.reply);
        }
      } catch (err) {
        addMessage("Не удалось отправить фото.", "companion");
      } finally {
        sceneInput.value = "";
      }
    });
  }

  // --- Speech-to-Text (распознавание) с barge-in ---
  const SpeechRecognitionImpl = window.SpeechRecognition || window.webkitSpeechRecognition;
  let recognition = null;
  let recognitionActive = false; // пользователь включил микрофон
  let recognitionRunning = false; // сейчас реально идёт сессия распознавания

  if (SpeechRecognitionImpl) {
    recognition = new SpeechRecognitionImpl();
    recognition.lang = "ru-RU";
    recognition.continuous = true;
    recognition.interimResults = true;

    recognition.onresult = (event) => {
      // Barge-in: как только слышим хоть что-то (даже промежуточный
      // результат), пока собеседник говорит — прерываем озвучку.
      if (isSpeaking) {
        window.speechSynthesis.cancel();
        isSpeaking = false;
        avatarEl.classList.remove("is-speaking");
        setStatus("Слушаю...");
      }

      let finalText = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        if (event.results[i].isFinal) finalText += event.results[i][0].transcript;
      }
      finalText = finalText.trim();
      if (finalText) {
        addMessage(finalText, "user");
        sendTurn({ text: finalText });
      }
    };

    recognition.onend = () => {
      recognitionRunning = false;
      if (recognitionActive && !limitReached) {
        // Браузер сам останавливает распознавание после паузы — если
        // пользователь не выключал микрофон вручную, перезапускаем.
        try {
          recognition.start();
          recognitionRunning = true;
        } catch (err) { /* уже запущено — игнорируем */ }
      } else {
        setStatus("Готов слушать");
      }
    };

    recognition.onerror = (event) => {
      if (event.error === "not-allowed" || event.error === "service-not-allowed") {
        recognitionActive = false;
        micBtn.classList.remove("is-listening");
        setStatus("Доступ к микрофону запрещён");
      }
    };

    micBtn.addEventListener("click", () => {
      if (limitReached) return;
      recognitionActive = !recognitionActive;
      micBtn.classList.toggle("is-listening", recognitionActive);
      if (recognitionActive) {
        setStatus("Слушаю...");
        try {
          recognition.start();
          recognitionRunning = true;
        } catch (err) { /* уже запущено */ }
      } else {
        setStatus("Готов слушать");
        recognition.stop();
      }
    });
  } else {
    micBtn.disabled = true;
    micBtn.title = "Голосовой ввод не поддерживается в этом браузере";
  }
})();
