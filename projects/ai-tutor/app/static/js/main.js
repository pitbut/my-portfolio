document.addEventListener("DOMContentLoaded", () => {
  const history = document.querySelector(".chat-history");
  if (history) {
    history.scrollTop = history.scrollHeight;
  }

  // Рендер формул LaTeX на доске (тип "formula"/"steps") — подключается
  // только на странице занятия, см. base.html {% if katex %}.
  if (window.renderMathInElement) {
    const board = document.querySelector(".board__content");
    if (board) {
      window.renderMathInElement(board, {
        delimiters: [
          { left: "$$", right: "$$", display: true },
          { left: "$", right: "$", display: false },
          { left: "\\(", right: "\\)", display: false },
          { left: "\\[", right: "\\]", display: true },
        ],
      });
    }
  }

  const photoInput = document.querySelector("#photo-input");
  const photoPreview = document.querySelector("#photo-preview");
  if (photoInput && photoPreview) {
    photoInput.addEventListener("change", () => {
      const file = photoInput.files[0];
      if (!file) {
        photoPreview.hidden = true;
        return;
      }
      photoPreview.src = URL.createObjectURL(file);
      photoPreview.hidden = false;
    });
  }
});
