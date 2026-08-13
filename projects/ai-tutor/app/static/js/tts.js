/* Озвучка реплик репетитора через Web Speech API (SpeechSynthesis) + анимация
 * 2D-аватара, синхронная с речью.
 *
 * Важное ограничение платформы: SpeechSynthesis не отдаёт свой аудиопоток
 * наружу — к нему нельзя подключить Web Audio API AnalyserNode и получать
 * реальную амплитуду голоса (это работает только с <audio>/<video> или
 * MediaStream, не с speechSynthesis). Поэтому рот синхронизируется не по
 * амплитуде, а по событиям `boundary` (граница каждого произнесённого
 * слова) — на практике визуально почти неотличимо для аватара такого
 * уровня детализации. Если `boundary` не пришёл ни разу в первую секунду
 * (часть голосов/браузеров его не поддерживает) — включается запасной
 * вариант: рот "болтается" по таймеру на всё время речи, без точной
 * привязки к словам. */

const MOUTH_STATES = ["closed", "mid", "open"];
const MOUTH_OPEN_MS = 150;
const BLINK_MIN_MS = 2500;
const BLINK_MAX_MS = 6000;
const BLINK_DURATION_MS = 120;
const BOUNDARY_WATCHDOG_MS = 700;
const FALLBACK_MOUTH_MIN_MS = 90;
const FALLBACK_MOUTH_MAX_MS = 200;

function findVoiceByName(name) {
  if (!name) return null;
  const voices = window.speechSynthesis.getVoices();
  return voices.find((v) => v.name === name) || null;
}

document.addEventListener("DOMContentLoaded", () => {
  const avatarEl = document.getElementById("avatar-widget");
  if (!avatarEl) return;

  const speechText = avatarEl.dataset.latestSpeech || "";
  const voiceName = avatarEl.dataset.voiceName || "";
  const autoplay = avatarEl.dataset.autoplay === "true";
  const subtitleEl = document.getElementById("avatar-subtitle");
  const micStatusEl = document.getElementById("mic-status");

  let speaking = false;
  let mouthTimer = null;
  let fallbackTimer = null;
  let watchdogTimer = null;
  let blinkTimer = null;
  // Срабатывает один раз, когда договаривает именно автовоспроизводимая при
  // загрузке страницы реплика (см. autoplay ниже) — stt.js использует это,
  // чтобы понять, когда включать тайм-аут ожидания ответа. Отдельные вызовы
  // speak(text, onEnd) (например, фраза "не расслышал, повтори") используют
  // собственный колбэк onEnd напрямую и с этим механизмом не связаны.
  let autoplayEndCallback = null;

  function setMouth(state) {
    avatarEl.classList.remove("mouth-closed", "mouth-mid", "mouth-open");
    avatarEl.classList.add(`mouth-${state}`);
  }

  function pulseMouth() {
    setMouth(MOUTH_STATES[1 + Math.floor(Math.random() * 2)]); // mid или open
    clearTimeout(mouthTimer);
    mouthTimer = setTimeout(() => setMouth("closed"), MOUTH_OPEN_MS);
  }

  function startFallbackMouthLoop() {
    stopFallbackMouthLoop();
    const tick = () => {
      pulseMouth();
      const delay = FALLBACK_MOUTH_MIN_MS + Math.random() * (FALLBACK_MOUTH_MAX_MS - FALLBACK_MOUTH_MIN_MS);
      fallbackTimer = setTimeout(tick, delay);
    };
    tick();
  }

  function stopFallbackMouthLoop() {
    clearTimeout(fallbackTimer);
    fallbackTimer = null;
  }

  function scheduleBlink() {
    const delay = BLINK_MIN_MS + Math.random() * (BLINK_MAX_MS - BLINK_MIN_MS);
    blinkTimer = setTimeout(() => {
      avatarEl.classList.add("is-blinking");
      setTimeout(() => avatarEl.classList.remove("is-blinking"), BLINK_DURATION_MS);
      scheduleBlink();
    }, delay);
  }

  function nod() {
    avatarEl.classList.remove("is-nodding");
    // reflow, чтобы анимацию можно было перезапустить на следующей же реплике
    void avatarEl.offsetWidth;
    avatarEl.classList.add("is-nodding");
  }

  function speak(text, onEnd) {
    if (!("speechSynthesis" in window) || !text) {
      if (onEnd) onEnd();
      return;
    }
    window.speechSynthesis.cancel();
    const utter = new SpeechSynthesisUtterance(text);
    const voice = findVoiceByName(voiceName);
    if (voice) utter.voice = voice;
    utter.lang = voice ? voice.lang : "ru-RU";

    let gotBoundary = false;

    utter.onstart = () => {
      speaking = true;
      nod();
      setMouth("mid");
      if (window.__subtitlesEnabled && subtitleEl) {
        subtitleEl.textContent = text;
        subtitleEl.hidden = false;
      }
      watchdogTimer = setTimeout(() => {
        if (!gotBoundary) startFallbackMouthLoop();
      }, BOUNDARY_WATCHDOG_MS);
    };

    utter.onboundary = (event) => {
      if (event.name && event.name !== "word") return;
      gotBoundary = true;
      stopFallbackMouthLoop();
      pulseMouth();
    };

    const finish = () => {
      speaking = false;
      clearTimeout(watchdogTimer);
      clearTimeout(mouthTimer);
      stopFallbackMouthLoop();
      setMouth("closed");
      if (subtitleEl) subtitleEl.hidden = true;
      if (onEnd) onEnd();
    };
    utter.onend = finish;
    utter.onerror = finish;

    window.speechSynthesis.speak(utter);
  }

  function stop() {
    window.speechSynthesis.cancel();
    speaking = false;
    clearTimeout(watchdogTimer);
    clearTimeout(mouthTimer);
    stopFallbackMouthLoop();
    setMouth("closed");
    if (subtitleEl) subtitleEl.hidden = true;
  }

  function isSpeaking() {
    return speaking;
  }

  function setMicStatus(text) {
    if (!micStatusEl) return;
    if (!text) {
      micStatusEl.hidden = true;
      return;
    }
    micStatusEl.textContent = text;
    micStatusEl.hidden = false;
  }

  function setOnEnd(callback) {
    autoplayEndCallback = callback;
  }

  // Публичный интерфейс для stt.js (barge-in, повторные вопросы при тишине,
  // индикатор "слушаю") — не зависит от порядка подключения скриптов.
  window.__tts = { speak, stop, isSpeaking, setMicStatus, setOnEnd };

  setMouth("closed");
  scheduleBlink();

  document.addEventListener("visibilitychange", () => {
    if (document.hidden) stop();
  });
  window.addEventListener("beforeunload", () => window.speechSynthesis.cancel());

  if (autoplay && speechText) {
    const start = () => speak(speechText, () => { if (autoplayEndCallback) autoplayEndCallback(); });
    if (window.speechSynthesis.getVoices().length) {
      start();
    } else {
      window.speechSynthesis.onvoiceschanged = start;
    }
  }
});
