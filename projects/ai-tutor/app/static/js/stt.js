/* Голосовой ввод — единственный способ ответить/спросить во время занятия
 * (фото решения — исключение, остаётся формой).
 *
 * Важно: микрофон включается ТОЛЬКО после того, как аватар закончил
 * говорить, никогда одновременно с воспроизведением его речи. Раньше
 * распознавание запускалось сразу при загрузке страницы, параллельно с
 * автовоспроизведением реплики — без наушников и аппаратного эхоподавления
 * микрофон улавливал звук из колонок (собственную озвучку аватара) и
 * ошибочно принимал обрывки её за ответ ученика (типичная акустическая
 * петля обратной связи). Поэтому barge-in в исходном смысле "перебить
 * прямо на середине фразы" здесь не поддержан — платформенных средств
 * надёжно отличить "ученик говорит поверх колонок" от "микрофон слышит
 * сами колонки" у Web Speech API нет. Вместо этого ученик может вставить
 * реплику сразу, как только аватар делает паузу (после реплики/вопроса) —
 * поскольку объяснение специально разбито на несколько ходов с
 * контрольными вопросами по ходу (раздел 3.1 промпта), такие паузы
 * случаются часто, а не только в самом конце.
 *
 * Два режима после того, как аватар замолчал:
 * - `barge-in` (STATE.awaiting = none) — слушаем без тайм-аута; если
 *   ученик что-то сказал — отправляем как обычное сообщение, модель сама
 *   решает, вопрос это или нет (раздел 5 промпта). Молчание — норма,
 *   ничего не происходит.
 * - `answer` (STATE.awaiting = student_answer/student_confirmation) —
 *   тайм-аут 18 сек. Тишина — один раз переспрашиваем голосом ("не
 *   расслышал, повтори") и ждём ещё 18 сек; вторая тишина — отправляем
 *   модели служебную пометку `NO_ANSWER_MARKER`. */

document.addEventListener("DOMContentLoaded", () => {
  const avatarEl = document.getElementById("avatar-widget");
  const form = document.getElementById("message-form");
  const textField = document.getElementById("message-text");
  const idleInput = document.getElementById("idle-seconds-input");
  if (!avatarEl || !form || !textField || !idleInput) return;
  if (avatarEl.dataset.lessonActive !== "true") return;

  const NO_ANSWER_MARKER = avatarEl.dataset.noAnswerMarker || "(ученик не ответил)";
  const awaiting = avatarEl.dataset.awaiting || "none";
  const answerMode = awaiting === "student_answer" || awaiting === "student_confirmation";
  const willSpeak = avatarEl.dataset.autoplay === "true";
  const ANSWER_TIMEOUT_MS = 18000;

  const SpeechRecognitionCtor = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognitionCtor) {
    if (window.__tts) {
      window.__tts.setMicStatus("Голосовой ввод не поддерживается этим браузером — отвечать голосом не получится.");
    }
    return;
  }

  let recognition = null;
  let active = true;
  let submitted = false;
  let answerTimer = null;
  let retryUsed = false;

  function submitText(text) {
    if (submitted) return;
    submitted = true;
    active = false;
    clearTimeout(answerTimer);
    if (recognition) {
      recognition.onend = null;
      recognition.stop();
    }
    textField.value = text;
    idleInput.value = String(Math.round((Date.now() - window.__lessonTurnShownAt) / 1000));
    form.requestSubmit ? form.requestSubmit() : form.submit();
  }

  function startRecognition() {
    recognition = new SpeechRecognitionCtor();
    recognition.lang = "ru-RU";
    recognition.continuous = true;
    recognition.interimResults = true;

    recognition.onresult = (event) => {
      const lastResult = event.results[event.results.length - 1];
      if (!lastResult.isFinal) return;

      const transcript = lastResult[0].transcript.trim();
      if (transcript.length < 2) return;
      submitText(transcript);
    };

    recognition.onend = () => {
      if (active) {
        try { recognition.start(); } catch (e) { /* уже запущено */ }
      }
    };

    recognition.onerror = (event) => {
      if (event.error === "not-allowed" || event.error === "service-not-allowed") {
        active = false;
        if (window.__tts) window.__tts.setMicStatus("Доступ к микрофону не разрешён — голосовой режим недоступен.");
      }
    };

    try { recognition.start(); } catch (e) { /* ... */ }
  }

  function armAnswerTimeout() {
    clearTimeout(answerTimer);
    answerTimer = setTimeout(() => {
      if (submitted || !active) return;

      if (!retryUsed) {
        retryUsed = true;
        if (window.__tts) {
          // Пока аватар переспрашивает — микрофон должен молчать, тот же
          // повод, что и в самом начале (не слушаем поверх своих же колонок).
          if (recognition) { recognition.onend = null; recognition.stop(); }
          window.__tts.setMicStatus("Не расслышал…");
          window.__tts.speak("Не расслышал, повтори, пожалуйста.", () => {
            if (submitted || !active) return;
            window.__tts.setMicStatus("🎤 Слушаю…");
            startRecognition();
            armAnswerTimeout();
          });
        }
      } else {
        submitText(NO_ANSWER_MARKER);
      }
    }, ANSWER_TIMEOUT_MS);
  }

  function beginListening() {
    if (!active) return;
    if (window.__tts) {
      window.__tts.setMicStatus(answerMode ? "🎤 Слушаю…" : "🎤 Можно спросить голосом…");
    }
    startRecognition();
    if (answerMode) armAnswerTimeout();
  }

  if (window.__tts) {
    window.__tts.setOnEnd(() => {
      if (submitted || !active) return;
      beginListening();
    });
  }

  if (willSpeak) {
    // Аватар вот-вот заговорит (автовоспроизведение реплики) — микрофон
    // включит beginListening() из колбэка setOnEnd выше, как только он
    // замолчит. Пока просто показываем, что он говорит.
    if (window.__tts) window.__tts.setMicStatus("🔊 Репетитор говорит…");
  } else {
    // Автовоспроизведения не будет (пустая реплика и т.п.) — слушать можно
    // сразу, колонки всё равно молчат.
    beginListening();
  }

  window.addEventListener("beforeunload", () => {
    active = false;
    if (recognition) {
      recognition.onend = null;
      recognition.stop();
    }
  });
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) {
      active = false;
      clearTimeout(answerTimer);
      if (recognition) {
        recognition.onend = null;
        recognition.stop();
      }
    }
  });
});
