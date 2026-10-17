/* Fond animé de molécules + vidéo de fond + champ de saisie bilingue (chargé par config.toml). */
(function () {
  // ---------- 1. Fond animé : atomes, liaisons et anneaux hexagonaux ----------
  var canvas = document.createElement("canvas");
  canvas.style.cssText =
    "position:fixed;inset:0;width:100%;height:100%;pointer-events:none;z-index:0;opacity:.4";
  document.body.appendChild(canvas);
  var ctx = canvas.getContext("2d");
  var W = 0, H = 0, atoms = [], rings = [];

  function resize() {
    W = canvas.width = window.innerWidth;
    H = canvas.height = window.innerHeight;
  }
  window.addEventListener("resize", resize);
  resize();

  function rnd(a, b) { return a + Math.random() * (b - a); }
  for (var i = 0; i < 48; i++) {
    atoms.push({ x: rnd(0, W), y: rnd(0, H), vx: rnd(-.25, .25), vy: rnd(-.25, .25), r: rnd(1.5, 3.2) });
  }
  for (var j = 0; j < 6; j++) {
    rings.push({ x: rnd(0, W), y: rnd(0, H), s: rnd(26, 70), a: rnd(0, 6.28), va: rnd(-.002, .002), vx: rnd(-.15, .15), vy: rnd(-.15, .15) });
  }

  function hexagone(x, y, s, a) {
    ctx.beginPath();
    for (var k = 0; k < 6; k++) {
      var t = a + k * Math.PI / 3;
      var px = x + s * Math.cos(t), py = y + s * Math.sin(t);
      if (k === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
    }
    ctx.closePath();
    ctx.stroke();
  }

  function frame() {
    ctx.clearRect(0, 0, W, H);
    ctx.lineWidth = 1;
    ctx.strokeStyle = "rgba(20,184,166,.28)";
    rings.forEach(function (r) {
      r.x += r.vx; r.y += r.vy; r.a += r.va;
      if (r.x < -80) r.x = W + 80; if (r.x > W + 80) r.x = -80;
      if (r.y < -80) r.y = H + 80; if (r.y > H + 80) r.y = -80;
      hexagone(r.x, r.y, r.s, r.a);
    });
    atoms.forEach(function (p) {
      p.x += p.vx; p.y += p.vy;
      if (p.x < 0 || p.x > W) p.vx *= -1;
      if (p.y < 0 || p.y > H) p.vy *= -1;
    });
    for (var a = 0; a < atoms.length; a++) {
      for (var b = a + 1; b < atoms.length; b++) {
        var dx = atoms[a].x - atoms[b].x, dy = atoms[a].y - atoms[b].y;
        var d = Math.sqrt(dx * dx + dy * dy);
        if (d < 140) {
          ctx.strokeStyle = "rgba(20,184,166," + (0.35 * (1 - d / 140)) + ")";
          ctx.beginPath(); ctx.moveTo(atoms[a].x, atoms[a].y); ctx.lineTo(atoms[b].x, atoms[b].y); ctx.stroke();
        }
      }
    }
    ctx.fillStyle = "rgba(20,184,166,.7)";
    atoms.forEach(function (p) { ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, 6.2832); ctx.fill(); });
    requestAnimationFrame(frame);
  }
  frame();

  // ---------- 2. Texte du champ de saisie : bilingue ----------
  var PH = "Posez votre question… / Ask your question…";
  var VIEUX = /Type your message here|Tapez votre message/;
  function corrigerPlaceholder() {
    document.querySelectorAll("[placeholder],[data-placeholder]").forEach(function (el) {
      ["placeholder", "data-placeholder"].forEach(function (attr) {
        var v = el.getAttribute(attr);
        if (v && VIEUX.test(v)) el.setAttribute(attr, PH);
      });
    });
  }
  new MutationObserver(corrigerPlaceholder).observe(document.body, {
    childList: true, subtree: true, attributes: true, attributeFilter: ["placeholder", "data-placeholder"]
  });
  corrigerPlaceholder();

  // ---------- 2b. Vidéo de fond de la page de chat + reflet qui suit la souris ----------
  var vf = document.createElement("video");
  vf.id = "fond-chat"; vf.autoplay = true; vf.muted = true; vf.loop = true; vf.playsInline = true;
  vf.src = "/public/fond.mp4?v=3";
  vf.style.cssText = "position:fixed;inset:0;width:100%;height:100%;object-fit:cover;z-index:0;" +
                     "filter:blur(2px) saturate(.9);transform:scale(1.05);pointer-events:none";
  var voile = document.createElement("div"); voile.id = "fond-voile";
  vf.addEventListener("error", function () { vf.remove(); voile.remove(); });  // pas de vidéo : on garde les molécules
  vf.addEventListener("loadeddata", function () { canvas.style.display = "none"; });
  var lente = function () { vf.playbackRate = 0.5; };
  vf.addEventListener("loadedmetadata", lente); vf.addEventListener("play", lente);
  document.body.insertBefore(voile, document.body.firstChild);
  document.body.insertBefore(vf, document.body.firstChild);
  document.addEventListener("mousemove", function (e) {
    var el = e.target.closest && e.target.closest("#welcome-screen button, div.rounded-3xl");
    if (!el) return;
    var r = el.getBoundingClientRect();
    el.style.setProperty("--mx", (e.clientX - r.left) + "px");
    el.style.setProperty("--my", (e.clientY - r.top) + "px");
  });

  // ---------- 3. Page de connexion personnalisée (fichier séparé, sans cache) ----------
  var sc = document.createElement("script");
  sc.src = "/public/connexion.js?v=" + Date.now();
  document.head.appendChild(sc);
})();