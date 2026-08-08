// Модуль 4 — карта исполнителей/продавцов/конструкторов и геопоиск «рядом».
// Обычный DOM + Leaflet, без сборщиков и фреймворков.
(function () {
  "use strict";

  var KIND_LABELS = { executor: "Исполнитель", constructor: "Конструктор", seller: "Продавец (барахолка)" };
  var ORG_TYPE_LABELS = { master: "Мастер", tsekh: "Цех", zavod: "Завод" };

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

    var filtersForm = document.getElementById("mapFilters");
    if (filtersForm && filtersForm.dataset.constructorsView === "1") {
      document.getElementById("f_design_engineer").checked = true;
      document.getElementById("f_kind_constructor").checked = true;
    }

    var selectedInfo = document.getElementById("selectedInfo");

    function describeItem(item) {
      var lines = ["<strong>" + item.name + "</strong>", KIND_LABELS[item.kind] || item.kind];
      if (item.org_type) lines[1] += " · " + (ORG_TYPE_LABELS[item.org_type] || item.org_type);
      if (item.region) lines.push(item.region);
      if (item.rating_avg) lines.push("Рейтинг: " + item.rating_avg.toFixed(1));
      if (item.experience_years) lines.push("Опыт: " + item.experience_years + " лет");
      if (item.services && item.services.length) lines.push(item.services.join(", "));
      if (item.has_design_engineer) lines.push("✏️ Есть конструктор в штате");
      if (item.kind === "seller") {
        lines.push(item.intent === "sell" ? "Продаю" : "Куплю");
        if (item.price) lines.push(item.price + " " + item.currency);
      }
      if (item.distance_km !== undefined) lines.push("Расстояние: " + item.distance_km + " км");
      return lines;
    }

    function popupHtml(item) {
      var lines = describeItem(item);
      var html = lines[0] + "<br>" + lines.slice(1).join("<br>");
      if (item.detail_url) html += '<br><a href="' + item.detail_url + '">Открыть →</a>';
      if (item.user_id) html += ' · <a href="/messages/u/' + item.user_id + '">✉ Написать</a>';
      return html;
    }

    function showSelectedInfo(item) {
      var lines = describeItem(item);
      var html = "<h3>" + lines[0] + "</h3><p>" + lines.slice(1).join(" · ") + "</p>";
      if (item.detail_url) html += '<a href="' + item.detail_url + '" class="btn btn--primary">Открыть портфолио →</a>';
      if (item.user_id) html += ' <a href="/messages/u/' + item.user_id + '" class="btn-link">✉ Написать</a>';
      selectedInfo.innerHTML = html;
      selectedInfo.hidden = false;
    }

    function addMarker(item) {
      var marker = L.marker([item.lat, item.lng]).addTo(markersLayer).bindPopup(popupHtml(item));
      marker.on("click", function () { showSelectedInfo(item); });
    }

    function selectedKinds() {
      var kinds = [];
      if (document.getElementById("f_kind_seller").checked) kinds.push("seller");
      if (document.getElementById("f_kind_executor").checked) kinds.push("executor");
      if (document.getElementById("f_kind_constructor").checked) kinds.push("constructor");
      return kinds;
    }

    function loadLayer() {
      markersLayer.clearLayers();
      selectedInfo.hidden = true;

      var region = document.getElementById("f_region").value;
      var kinds = selectedKinds();

      if (kinds.indexOf("executor") !== -1) {
        var execParams = new URLSearchParams();
        var service = document.getElementById("f_service").value;
        var orgType = document.getElementById("f_org_type").value;
        var designEngineer = document.getElementById("f_design_engineer").checked;
        if (service) execParams.set("service_category_id", service);
        if (orgType) execParams.set("org_type", orgType);
        if (region) execParams.set("region_id", region);
        if (designEngineer) execParams.set("has_design_engineer", "1");
        fetch("/map/executors.json?" + execParams.toString())
          .then(function (r) { return r.json(); })
          .then(function (items) { items.forEach(addMarker); });
      }

      if (kinds.indexOf("constructor") !== -1) {
        var constrParams = new URLSearchParams();
        if (region) constrParams.set("region_id", region);
        fetch("/map/constructors.json?" + constrParams.toString())
          .then(function (r) { return r.json(); })
          .then(function (items) { items.forEach(addMarker); });
      }

      if (kinds.indexOf("seller") !== -1) {
        var sellerParams = new URLSearchParams();
        if (region) sellerParams.set("region_id", region);
        fetch("/map/sellers.json?" + sellerParams.toString())
          .then(function (r) { return r.json(); })
          .then(function (items) { items.forEach(addMarker); });
      }
    }

    ["f_kind_seller", "f_kind_executor", "f_kind_constructor", "f_service", "f_org_type", "f_region", "f_design_engineer"].forEach(function (id) {
      document.getElementById(id).addEventListener("change", loadLayer);
    });
    loadLayer();

    var nearbyBtn = document.getElementById("btnNearby");
    var manualBtn = document.getElementById("btnManualPin");
    var manualHint = document.getElementById("manualPinHint");
    var nearbyBlock = document.getElementById("nearbyResults");
    var nearbyList = document.getElementById("nearbyList");
    var manualMode = false;

    function placeUserMarker(lat, lng) {
      if (userMarker) map.removeLayer(userMarker);
      userMarker = L.circleMarker([lat, lng], { radius: 8, color: "#FFA500" }).addTo(map).bindPopup("Вы здесь");
      map.setView([lat, lng], 10);
      loadNearby(lat, lng);
    }

    function loadNearby(lat, lng) {
      var kinds = selectedKinds();
      if (!kinds.length) kinds = ["executor"];
      fetch("/map/nearby.json?lat=" + lat + "&lng=" + lng + "&radius_km=50&kinds=" + kinds.join(","))
        .then(function (r) { return r.json(); })
        .then(function (items) {
          nearbyBlock.hidden = false;
          if (!items.length) {
            nearbyList.innerHTML = "<p class=\"empty-hint\">В радиусе 50 км никого не найдено.</p>";
            return;
          }
          nearbyList.innerHTML = items.map(function (item) {
            return '<div class="notif-item"><div class="notif-item__title">' + item.name + " — " + item.distance_km + ' км</div>' +
              '<div class="notif-item__body">' + (KIND_LABELS[item.kind] || item.kind) + (item.region ? " · " + item.region : "") +
              (item.services && item.services.length ? " · " + item.services.join(", ") : "") + "</div></div>";
          }).join("");
        });
    }

    nearbyBtn.addEventListener("click", function () {
      if (!navigator.geolocation) {
        alert("Геолокация не поддерживается браузером. Нажмите «✋ Указать себя на карте» и отметьте точку кликом.");
        return;
      }
      nearbyBtn.disabled = true;
      nearbyBtn.textContent = "Определяем местоположение…";
      navigator.geolocation.getCurrentPosition(
        function (pos) {
          nearbyBtn.disabled = false;
          nearbyBtn.textContent = "📍 Показать рядом со мной";
          placeUserMarker(pos.coords.latitude, pos.coords.longitude);
        },
        function () {
          nearbyBtn.disabled = false;
          nearbyBtn.textContent = "📍 Показать рядом со мной";
          alert("Не удалось определить местоположение автоматически. Нажмите «✋ Указать себя на карте» и отметьте точку кликом вручную.");
        }
      );
    });

    manualBtn.addEventListener("click", function () {
      manualMode = !manualMode;
      manualHint.hidden = !manualMode;
      manualBtn.textContent = manualMode ? "✋ Отменить" : "✋ Указать себя на карте";
    });

    map.on("click", function (e) {
      if (!manualMode) return;
      manualMode = false;
      manualHint.hidden = true;
      manualBtn.textContent = "✋ Указать себя на карте";
      placeUserMarker(e.latlng.lat, e.latlng.lng);
    });
  });
})();
