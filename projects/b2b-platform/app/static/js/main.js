// Общий JS: paywall-модалка, каскад «регион -> город», карта выбора локации.
// Никаких фреймворков — обычный DOM, чтобы не тянуть сборку в маленький проект.

(function () {
  "use strict";

  function initAuthModal() {
    var modal = document.getElementById("authModal");
    if (!modal) return;

    modal.querySelectorAll("[data-close-modal]").forEach(function (el) {
      el.addEventListener("click", function () {
        modal.classList.remove("is-open");
        modal.setAttribute("aria-hidden", "true");
      });
    });

    var tabs = modal.querySelectorAll(".modal__tab");
    tabs.forEach(function (tab) {
      tab.addEventListener("click", function () {
        tabs.forEach(function (t) { t.classList.remove("is-active"); });
        tab.classList.add("is-active");
        var target = tab.getAttribute("data-tab");
        modal.querySelectorAll(".modal__panel").forEach(function (panel) {
          panel.hidden = panel.getAttribute("data-panel") !== target;
        });
      });
    });
  }

  // Экспортируется глобально — вызывается из inline-скрипта конкретной
  // страницы профиля, где известны id полей региона/города.
  window.initRegionCityCascade = function (regionSelectId, citySelectId) {
    var regionSelect = document.getElementById(regionSelectId);
    var citySelect = document.getElementById(citySelectId);
    if (!regionSelect || !citySelect) return;

    function loadCities(regionId, preselectId) {
      if (!regionId) {
        citySelect.innerHTML = '<option value="">— сначала выберите регион —</option>';
        return;
      }
      citySelect.disabled = true;
      citySelect.innerHTML = '<option value="">Загрузка…</option>';
      fetch("/profile/cities/" + regionId + ".json", { headers: { "X-Requested-With": "XMLHttpRequest" } })
        .then(function (res) { return res.json(); })
        .then(function (cities) {
          var options = ['<option value="">— не выбран —</option>'];
          cities.forEach(function (city) {
            var selected = String(city.id) === String(preselectId) ? " selected" : "";
            options.push('<option value="' + city.id + '"' + selected + ">" + city.name + "</option>");
          });
          citySelect.innerHTML = options.join("");
          citySelect.disabled = false;
        })
        .catch(function () {
          citySelect.innerHTML = '<option value="">Не удалось загрузить города</option>';
          citySelect.disabled = false;
        });
    }

    regionSelect.addEventListener("change", function () {
      loadCities(regionSelect.value, null);
    });

    var initialRegion = regionSelect.value;
    var preselectedCity = citySelect.getAttribute("data-selected");
    if (initialRegion) {
      loadCities(initialRegion, preselectedCity);
    }
  };

  // Карта на Leaflet (OpenStreetMap, без API-ключа): клик или перетаскивание
  // маркера обновляют скрытые поля широты/долготы формы.
  window.initLocationMap = function (mapElId, latFieldId, lngFieldId) {
    var mapEl = document.getElementById(mapElId);
    if (!mapEl || typeof L === "undefined") return;

    var latField = document.getElementById(latFieldId);
    var lngField = document.getElementById(lngFieldId);

    var savedLat = parseFloat(mapEl.getAttribute("data-lat"));
    var savedLng = parseFloat(mapEl.getAttribute("data-lng"));
    var hasSaved = !isNaN(savedLat) && !isNaN(savedLng);

    // Центр Узбекистана (Ташкент) по умолчанию, если точка ещё не выбрана.
    var start = hasSaved ? [savedLat, savedLng] : [41.3111, 69.2797];

    var map = L.map(mapEl).setView(start, hasSaved ? 12 : 6);
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

  // Кнопка «Найти на карте» рядом с текстовым полем адреса: подтягивает
  // точку через бесплатный геокодер Nominatim (OpenStreetMap, без ключа —
  // как и сама карта). Адрес — обычный текст «на глаз», может быть неточным
  // или неполным (без номера дома), поэтому маркер после этого остаётся
  // перетаскиваемым, а не выставляется намертво — геокодирование лишь
  // подсказка, а не источник истины. У Nominatim есть лимит по частоте
  // запросов — годится для формы профиля (клик по кнопке вручную), но не для
  // массовых/фоновых вызовов.
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

      fetch("https://nominatim.openstreetmap.org/search?format=json&limit=1&countrycodes=uz&q=" + encodeURIComponent(query))
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

  document.addEventListener("DOMContentLoaded", initAuthModal);
})();
