/* Голосовой ввод — единственный способ ответить/спросить во время занятия
 * (фото решения — исключение, остаётся формой). Одна непрерывная сессия
 * распознавания на всё время, пока страница занятия открыта, с двумя
 * режимами поведения:
 *
 * - `barge-in` (STATE.awaiting = none, аватар просто рассказывает) —
 *   слушаем без тайм-аута; если ученик что-то сказал — отправляем как
 *   обычное сообщение, модель сама решает, вопрос это или нет (раздел 5
 *   промпта). Если ученик молчит — ничего не происходит, это нормально.
 * - `answer` (STATE.awaiting = student_answer/student_confirmation —
 *   контрольный вопрос по ходу объяснения или ответ по существу) — как
 *   только аватар договорил вопрос, включается тайм-аут 18 сек. Тишина —
 *   один раз переспрашиваем голосом ("не расслышал, повтори") и ждём ещё
 *   18 сек; вторая тишина — отправляем модели служебную пометку
 *   `NO_ANSWER_MARKER`, дальше по этому разбирается сам промпт.
 *
 * В обоих режимах любой звук речи ученика немедленно ставит озвучку
 * аватара на паузу (barge-in), пока идёт объяснение/вопрос. */

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
      if (window.__tts && window.__tts.isSpeaking()) window.__tts.pause();

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
          window.__tts.setMicStatus("Не расслышал…");
          window.__tts.speak("Не расслышал, повтори, пожалуйста.", () => {
            if (submitted || !active) return;
            window.__tts.setMicStatus("🎤 Слушаю…");
            armAnswerTimeout();
          });
        }
      } else {
        submitText(NO_ANSWER_MARKER);
      }
    }, ANSWER_TIMEOUT_MS);
  }

  if (window.__tts) {
    window.__tts.setOnEnd(() => {
      if (submitted || !active) return;
      if (answerMode) {
        window.__tts.setMicStatus("🎤 Слушаю…");
        armAnswerTimeout();
      } else {
        window.__tts.setMicStatus("🎤 Можно спросить голосом…");
      }
    });
    window.__tts.setMicStatus(answerMode ? "🎤" : "🎤 Можно спросить голосом…");
  }

  startRecognition();

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
