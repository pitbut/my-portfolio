// Лёгкий эффект «всплытия» карточек при появлении в зоне видимости.
document.addEventListener("DOMContentLoaded", () => {
  const cards = document.querySelectorAll(".card, .fact-card");
  if (!("IntersectionObserver" in window) || cards.length === 0) return;

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.style.opacity = "1";
          entry.target.style.transform = "translateY(0)";
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.1 }
  );

  cards.forEach((card, i) => {
    card.style.opacity = "0";
    card.style.transform = "translateY(16px)";
    card.style.transition = `opacity .5s ease ${i % 6 * 0.05}s, transform .5s ease ${i % 6 * 0.05}s`;
    observer.observe(card);
  });
});
