/* Озвучка реплик репетитора через Web Speech API (SpeechSynthesis) —
 * раздел 9.2 ТЗ ("аватар с анимацией и TTS-озвучкой"). Работает целиком в
 * браузере, без серверного TTS-провайдера и отдельного ключа — голос и
 * его мгновенная пауза/остановка (раздел 9 ТЗ, НФТ) обеспечиваются
 * нативным SpeechSynthesis. */

function findVoiceByName(name) {
  if (!name) return null;
  const voices = window.speechSynthesis.getVoices();
  return voices.find((v) => v.name === name) || null;
}

function speak(text, voiceName, onStart, onEnd) {
  if (!("speechSynthesis" in window) || !text) {
    if (onEnd) onEnd();
    return;
  }
  window.speechSynthesis.cancel();
  const utter = new SpeechSynthesisUtterance(text);
  const voice = findVoiceByName(voiceName);
  if (voice) utter.voice = voice;
  utter.lang = voice ? voice.lang : "ru-RU";
  if (onStart) utter.onstart = onStart;
  if (onEnd) { utter.onend = onEnd; utter.onerror = onEnd; }
  window.speechSynthesis.speak(utter);
}

document.addEventListener("DOMContentLoaded", () => {
  const avatarEl = document.querySelector(".avatar-widget");
  if (!avatarEl) return;

  const speechText = avatarEl.dataset.latestSpeech || "";
  const voiceName = avatarEl.dataset.voiceName || "";
  const autoplay = avatarEl.dataset.autoplay === "true";
  const toggleBtn = avatarEl.querySelector(".avatar-widget__toggle");

  const setTalking = (talking) => avatarEl.classList.toggle("is-talking", talking);

  function play() {
    if (!speechText) return;
    setTalking(true);
    if (toggleBtn) toggleBtn.textContent = "⏸️";
    speak(speechText, voiceName, () => setTalking(true), () => {
      setTalking(false);
      if (toggleBtn) toggleBtn.textContent = "🔊";
    });
  }

  function stop() {
    window.speechSynthesis.cancel();
    setTalking(false);
    if (toggleBtn) toggleBtn.textContent = "🔊";
  }

  function pause() {
    if ("speechSynthesis" in window && window.speechSynthesis.speaking) {
      window.speechSynthesis.pause();
      setTalking(false);
    }
  }

  function resume() {
    if ("speechSynthesis" in window && window.speechSynthesis.paused) {
      window.speechSynthesis.resume();
      setTalking(true);
    }
  }

  // Даёт stt.js мгновенно прервать озвучку в момент, когда распознан голос
  // ученика (barge-in, раздел 4.4/9.3 ТЗ), не завися от порядка подключения
  // скриптов на странице.
  window.__tts = { play, stop, pause, resume };

  if (toggleBtn) {
    toggleBtn.addEventListener("click", () => {
      if (window.speechSynthesis.speaking) {
        stop();
      } else {
        play();
      }
    });
  }

  // Мгновенная остановка при уходе со страницы/скрытии вкладки.
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) stop();
  });
  window.addEventListener("beforeunload", () => window.speechSynthesis.cancel());

  if (autoplay && speechText) {
    // getVoices() иногда пуст при первом вызове — голоса подгружаются
    // асинхронно, дожидаемся события перед автовоспроизведением.
    if (window.speechSynthesis.getVoices().length) {
      play();
    } else {
      window.speechSynthesis.onvoiceschanged = play;
    }
  }
});
