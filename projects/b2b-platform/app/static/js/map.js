// Модуль 4 — карта исполнителей и геопоиск «рядом». Обычный DOM + Leaflet,
// без сборщиков и фреймворков.
(function () {
  "use strict";

  document.addEventListener("DOMContentLoaded", function () {
    var mapEl = document.getElementById("executorsMap");
    if (!mapEl || typeof L === "undefined") return;

    var map = L.map(mapEl).setView([41.3111, 69.2797], 6);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "&copy; OpenStreetMap contributors",
      maxZoom: 18,
    }).addTo(map);

    var markersLayer = L.layerGroup().addTo(map);
    var userMarker = null;

    function popupHtml(item) {
      var typeLabels = { master: "Мастер", tsekh: "Цех", zavod: "Завод" };
      var html = "<strong>" + item.name + "</strong><br>" + (typeLabels[item.org_type] || item.org_type);
      if (item.region) html += " · " + item.region;
      if (item.rating_avg) html += "<br>Рейтинг: " + item.rating_avg.toFixed(1);
      if (item.distance_km !== undefined) html += "<br>Расстояние: " + item.distance_km + " км";
      if (item.services && item.services.length) html += "<br>" + item.services.join(", ");
      if (item.has_design_engineer) html += "<br>✏️ Есть конструктор в штате";
      if (item.user_id) html += '<br><a href="/messages/u/' + item.user_id + '">✉ Написать</a>';
      return html;
    }

    function loadExecutors() {
      var params = new URLSearchParams();
      var service = document.getElementById("f_service").value;
      var orgType = document.getElementById("f_org_type").value;
      var region = document.getElementById("f_region").value;
      var designEngineer = document.getElementById("f_design_engineer").checked;
      if (service) params.set("service_category_id", service);
      if (orgType) params.set("org_type", orgType);
      if (region) params.set("region_id", region);
      if (designEngineer) params.set("has_design_engineer", "1");

      fetch("/map/executors.json?" + params.toString())
        .then(function (r) { return r.json(); })
        .then(function (items) {
          markersLayer.clearLayers();
          items.forEach(function (item) {
            L.marker([item.lat, item.lng]).addTo(markersLayer).bindPopup(popupHtml(item));
          });
        });
    }

    ["f_service", "f_org_type", "f_region", "f_design_engineer"].forEach(function (id) {
      document.getElementById(id).addEventListener("change", loadExecutors);
    });
    loadExecutors();

    var nearbyBtn = document.getElementById("btnNearby");
    var nearbyBlock = document.getElementById("nearbyResults");
    var nearbyList = document.getElementById("nearbyList");

    nearbyBtn.addEventListener("click", function () {
      if (!navigator.geolocation) {
        alert("Геолокация не поддерживается браузером — введите адрес вручную в профиле.");
        return;
      }
      nearbyBtn.disabled = true;
      nearbyBtn.textContent = "Определяем местоположение…";
      navigator.geolocation.getCurrentPosition(
        function (pos) {
          var lat = pos.coords.latitude, lng = pos.coords.longitude;
          nearbyBtn.disabled = false;
          nearbyBtn.textContent = "📍 Показать рядом со мной";

          if (userMarker) map.removeLayer(userMarker);
          userMarker = L.circleMarker([lat, lng], { radius: 8, color: "#FFA500" }).addTo(map).bindPopup("Вы здесь");
          map.setView([lat, lng], 10);

          fetch("/map/nearby.json?lat=" + lat + "&lng=" + lng + "&radius_km=50")
            .then(function (r) { return r.json(); })
            .then(function (items) {
              nearbyBlock.hidden = false;
              if (!items.length) {
                nearbyList.innerHTML = "<p class=\"empty-hint\">В радиусе 50 км исполнителей не найдено.</p>";
                return;
              }
              nearbyList.innerHTML = items.map(function (item) {
                return '<div class="notif-item"><div class="notif-item__title">' + item.name + " — " + item.distance_km + ' км</div>' +
                  '<div class="notif-item__body">' + (item.region || "") + (item.services.length ? " · " + item.services.join(", ") : "") + "</div></div>";
              }).join("");
            });
        },
        function () {
          nearbyBtn.disabled = false;
          nearbyBtn.textContent = "📍 Показать рядом со мной";
          alert("Не удалось определить местоположение. Проверьте разрешение геолокации в браузере.");
        }
      );
    });
  });
})();
