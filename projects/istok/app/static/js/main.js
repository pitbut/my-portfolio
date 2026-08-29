// Карта на Leaflet (OpenStreetMap, без API-ключа) для выбора точки продажи:
// клик или перетаскивание маркера обновляют скрытые поля широты/долготы формы.
// Вызывается только со страниц, где есть нужные элементы (см. add_supplier.html).
window.initLocationMap = function (mapElId, latFieldId, lngFieldId) {
  var mapEl = document.getElementById(mapElId);
  if (!mapEl || typeof L === "undefined") return null;

  var latField = document.getElementById(latFieldId);
  var lngField = document.getElementById(lngFieldId);

  var savedLat = parseFloat(mapEl.getAttribute("data-lat"));
  var savedLng = parseFloat(mapEl.getAttribute("data-lng"));
  var hasSaved = !isNaN(savedLat) && !isNaN(savedLng);

  // Центр — примерно Москва, если точка ещё не выбрана (в основном сюда
  // добавляют точки продажи; карту всё равно можно свободно листать/зумить).
  var start = hasSaved ? [savedLat, savedLng] : [55.7522, 37.6156];

  var map = L.map(mapEl).setView(start, hasSaved ? 13 : 4);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "&copy; OpenStreetMap contributors",
    maxZoom: 18,
  }).addTo(map);

  var marker = hasSaved ? L.marker(start, { draggable: true }).addTo(map) : null;

  function setPoint(lat, lng) {
    latField.value = lat.toFixed(6);
    lngField.value = lng.toFixed(6);
    if (marker) {
      marker.setLatLng([lat, lng]);
    } else {
      marker = L.marker([lat, lng], { draggable: true }).addTo(map);
      marker.on("dragend", function () {
        var pos = marker.getLatLng();
        setPoint(pos.lat, pos.lng);
      });
    }
  }

  if (marker) {
    marker.on("dragend", function () {
      var pos = marker.getLatLng();
      setPoint(pos.lat, pos.lng);
    });
  }

  map.on("click", function (e) {
    setPoint(e.latlng.lat, e.latlng.lng);
  });

  return { setPoint: setPoint, map: map };
};

// Кнопка «Найти на карте» рядом с полем адреса: подтягивает точку через
// бесплатный геокодер Nominatim (OpenStreetMap, без ключа — как и сама
// карта). Адрес — обычный текст «на глаз», может быть неточным, поэтому
// маркер после этого остаётся перетаскиваемым, а не выставляется намертво.
// У Nominatim есть лимит по частоте запросов — годится для формы с ручным
// нажатием кнопки, но не для массовых/фоновых вызовов.
window.initAddressGeocode = function (buttonId, addressFieldId, mapController) {
  var btn = document.getElementById(buttonId);
  var addressField = document.getElementById(addressFieldId);
  if (!btn || !addressField || !mapController) return;

  btn.addEventListener("click", function () {
    var query = addressField.value.trim();
    if (!query) {
      alert("Сначала введите адрес.");
      return;
    }
    var originalText = btn.textContent;
    btn.disabled = true;
    btn.textContent = "Ищу…";

    fetch("https://nominatim.openstreetmap.org/search?format=json&limit=1&q=" + encodeURIComponent(query))
      .then(function (res) { return res.json(); })
      .then(function (results) {
        if (!results.length) {
          alert("Не удалось найти это место на карте. Уточните адрес или отметьте точку вручную кликом.");
          return;
        }
        var lat = parseFloat(results[0].lat);
        var lon = parseFloat(results[0].lon);
        mapController.setPoint(lat, lon);
        mapController.map.setView([lat, lon], 15);
      })
      .catch(function () {
        alert("Не удалось связаться с картографическим сервисом. Отметьте точку на карте вручную.");
      })
      .finally(function () {
        btn.disabled = false;
        btn.textContent = originalText;
      });
  });
};

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
