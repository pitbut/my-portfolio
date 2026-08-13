/* Сигнал "ученик на месте" с камеры — не распознавание лиц/эмоций (это
 * отдельный тяжёлый путь через vision-API, раздел 9.3 ТЗ и так не требовал
 * его для MVP, см. README), а простое сравнение соседних кадров: если в
 * кадре давно нет движения — скорее всего, никого нет перед камерой.
 * Обработка целиком на клиенте, кадры никуда не отправляются — ни на
 * сервер, ни в ИИ-API, только средняя яркость сравнивается в памяти
 * страницы. Если доступа к камере нет/не дали — не блокируем занятие,
 * stt.js просто откатывается на прежнюю логику (два хода без ответа
 * подряд, без сигнала присутствия). */

const MOTION_SAMPLE_MS = 1500;
const MOTION_GRID_W = 24;
const MOTION_GRID_H = 18;
const MOTION_THRESHOLD = 12; // средний перепад яркости пикселя (0-255); выше — считаем движением

document.addEventListener("DOMContentLoaded", () => {
  // Безопасный дефолт до того, как (если) камеру разрешат — stt.js должен
  // суметь спросить window.__presence сразу же, не дожидаясь этого файла.
  window.__presence = { hasCamera: false, recentMotion: () => true };

  const avatarEl = document.getElementById("avatar-widget");
  const videoEl = document.getElementById("presence-video");
  const canvasEl = document.getElementById("presence-canvas");
  const statusEl = document.getElementById("presence-status");
  const previewEl = document.getElementById("presence-preview");
  if (!avatarEl || avatarEl.dataset.lessonActive !== "true" || !videoEl || !canvasEl) return;
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) return;

  let lastMotionAt = Date.now();
  let prevFrame = null;
  let sampleTimer = null;
  const ctx = canvasEl.getContext("2d", { willReadFrequently: true });
  canvasEl.width = MOTION_GRID_W;
  canvasEl.height = MOTION_GRID_H;

  function sampleFrame() {
    if (videoEl.readyState < 2) return;
    ctx.drawImage(videoEl, 0, 0, MOTION_GRID_W, MOTION_GRID_H);
    const frame = ctx.getImageData(0, 0, MOTION_GRID_W, MOTION_GRID_H).data;
    if (prevFrame) {
      let diffSum = 0;
      const pixels = MOTION_GRID_W * MOTION_GRID_H;
      for (let i = 0; i < frame.length; i += 4) {
        const prevLum = (prevFrame[i] + prevFrame[i + 1] + prevFrame[i + 2]) / 3;
        const curLum = (frame[i] + frame[i + 1] + frame[i + 2]) / 3;
        diffSum += Math.abs(curLum - prevLum);
      }
      if (diffSum / pixels > MOTION_THRESHOLD) lastMotionAt = Date.now();
    }
    prevFrame = frame;
  }

  navigator.mediaDevices
    .getUserMedia({ video: { width: 160, height: 120 }, audio: false })
    .then((stream) => {
      videoEl.srcObject = stream;
      window.__presence = {
        hasCamera: true,
        recentMotion(withinMs) {
          return Date.now() - lastMotionAt < withinMs;
        },
      };
      if (previewEl) previewEl.hidden = false;
      if (statusEl) {
        statusEl.textContent = "📷 Камера включена — помогает понять, что ты на месте";
        statusEl.hidden = false;
      }
      sampleTimer = setInterval(sampleFrame, MOTION_SAMPLE_MS);

      window.addEventListener("beforeunload", () => {
        stream.getTracks().forEach((t) => t.stop());
      });
      document.addEventListener("visibilitychange", () => {
        if (document.hidden) {
          clearInterval(sampleTimer);
          sampleTimer = null;
        } else if (!sampleTimer) {
          sampleTimer = setInterval(sampleFrame, MOTION_SAMPLE_MS);
        }
      });
    })
    .catch(() => {
      // Доступ не дали или камеры нет — тихо остаёмся с дефолтом выше,
      // занятие продолжается как раньше, просто без сигнала присутствия.
    });
});
