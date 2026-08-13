/* Голосовой ввод с barge-in: пока аватар озвучивает объяснение, ученик
 * может в любой момент задать вопрос голосом — раздел 4.4/9.3 ТЗ и раздел 5
 * ai-tutor-system-prompt.md ("Одновременное слушание"). Распознавание речи —
 * через Web Speech API (SpeechRecognition), без отдельного STT-провайдера
 * и ключа, тем же способом, что и озвучка в tts.js.
 *
 * Модель уже умеет отличать короткую реплику-подтверждение ("ага", "понял")
 * от настоящего вопроса и продолжать объяснение с того места, где
 * остановилась (см. раздел 5 промпта), поэтому здесь распознанный текст
 * просто отправляется как обычное сообщение — фильтровать реплики на
 * клиенте не нужно, это ответственность системного промпта. */

document.addEventListener("DOMContentLoaded", () => {
  const micBtn = document.getElementById("mic-toggle");
  const form = document.getElementById("message-form");
  const textField = document.getElementById("message-text");
  const idleInput = document.getElementById("idle-seconds-input");
  const listeningHint = document.getElementById("listening-hint");
  if (!micBtn || !form || !textField) return;

  const SpeechRecognitionCtor = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognitionCtor) {
    micBtn.disabled = true;
    micBtn.title = "Голосовой ввод не поддерживается этим браузером";
    return;
  }

  let recognition = null;
  let listening = false;
  let submitting = false;

  function startRecognition() {
    recognition = new SpeechRecognitionCtor();
    recognition.lang = "ru-RU";
    recognition.continuous = true;
    recognition.interimResults = true;

    recognition.onresult = (event) => {
      // Как только распознан хоть один звук речи — прерываем озвучку
      // аватара немедленно (мгновенная пауза, раздел 9 ТЗ, НФТ).
      if (window.__tts) window.__tts.pause();
      if (listeningHint) listeningHint.hidden = false;

      const lastResult = event.results[event.results.length - 1];
      if (!lastResult.isFinal) return;

      const transcript = lastResult[0].transcript.trim();
      if (transcript.length < 2 || submitting) return;

      submitting = true;
      textField.value = transcript;
      idleInput.value = "0";
      stopRecognition();
      form.requestSubmit ? form.requestSubmit() : form.submit();
    };

    recognition.onend = () => {
      if (listening && !submitting) {
        // continuous-режим иногда всё равно завершается сам — перезапускаем,
        // пока ученик не выключил микрофон вручную.
        try { recognition.start(); } catch (e) { /* уже запущено */ }
      }
    };

    recognition.onerror = (event) => {
      if (event.error === "not-allowed" || event.error === "service-not-allowed") {
        listening = false;
        micBtn.classList.remove("is-active");
        micBtn.textContent = "🎤";
        alert("Доступ к микрофону не разрешён — голосовой режим недоступен.");
      }
    };

    recognition.start();
  }

  function stopRecognition() {
    if (recognition) {
      recognition.onend = null;
      recognition.stop();
    }
    if (listeningHint) listeningHint.hidden = true;
  }

  micBtn.addEventListener("click", () => {
    listening = !listening;
    micBtn.classList.toggle("is-active", listening);
    micBtn.textContent = listening ? "🎤" : "🎤";
    micBtn.title = listening
      ? "Выключить голосовой режим"
      : "Включить голосовой режим (можно задать вопрос голосом прямо во время объяснения)";

    if (listening) {
      startRecognition();
    } else {
      stopRecognition();
    }
  });

  window.addEventListener("beforeunload", () => stopRecognition());
});
