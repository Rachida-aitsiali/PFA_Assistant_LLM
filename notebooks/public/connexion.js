/* ChemAsk : page de connexion (se connecter / créer un compte / Google)
   Fond : vidéo public/fond.mp4 (si absente : molécules douces sur fond blanc). */
(function () {
  var T = {
    fr: {
      tag: "Votre assistant IA pour la chimie des médicaments",
      sub: "Cibles protéiques · molécules · bioactivités — ChEMBL & PubChem",
      in: "Se connecter", up: "Créer un compte",
      email: "Adresse e-mail", pw: "Mot de passe", pw2: "Confirmer le mot de passe",
      go_in: "Se connecter", go_up: "Créer mon compte",
      or: "ou", google: "Continuer avec Google",
      no_acc: "Pas encore de compte ?", has_acc: "Déjà un compte ?",
      e_bad: "E-mail ou mot de passe incorrect.",
      e_email: "Adresse e-mail invalide.", e_password: "Mot de passe : 6 caractères minimum.",
      e_exists: "Un compte existe déjà avec cet e-mail : connectez-vous.",
      e_match: "Les deux mots de passe sont différents.", e_net: "Erreur réseau, réessayez.",
      show: "Afficher", hide: "Masquer"
    },
    en: {
      tag: "Your AI assistant for medicinal chemistry",
      sub: "Protein targets · molecules · bioactivities — ChEMBL & PubChem",
      in: "Sign in", up: "Create account",
      email: "Email address", pw: "Password", pw2: "Confirm password",
      go_in: "Sign in", go_up: "Create my account",
      or: "or", google: "Continue with Google",
      no_acc: "No account yet?", has_acc: "Already have an account?",
      e_bad: "Wrong email or password.",
      e_email: "Invalid email address.", e_password: "Password: 6 characters minimum.",
      e_exists: "An account already exists with this email: please sign in.",
      e_match: "The two passwords do not match.", e_net: "Network error, please retry.",
      show: "Show", hide: "Hide"
    }
  };
  var lang = "fr", mode = "in", google = false, racine = null, raf = null;
  try {
    lang = localStorage.getItem("chemask-lang") || ((navigator.language || "fr").slice(0, 2) === "en" ? "en" : "fr");
  } catch (e) {}

  // ---------- fond de secours (si pas de vidéo) : molécules douces sur fond blanc ----------
  function fond(canvas) {
    var ctx = canvas.getContext("2d"), W, H, t = 0, atomes = [];
    function taille() { W = canvas.width = innerWidth; H = canvas.height = innerHeight; }
    taille(); addEventListener("resize", taille);
    for (var i = 0; i < 40; i++) {
      atomes.push({ x: Math.random(), y: Math.random(), vx: (Math.random() - .5) * 8e-5,
        vy: (Math.random() - .5) * 8e-5, r: 2 + Math.random() * 3.5 });
    }
    function frame() {
      t += 16;
      ctx.fillStyle = "#f8fafc"; ctx.fillRect(0, 0, W, H);
      atomes.forEach(function (p) {
        p.x += p.vx * 16; p.y += p.vy * 16;
        if (p.x < 0 || p.x > 1) p.vx *= -1;
        if (p.y < 0 || p.y > 1) p.vy *= -1;
      });
      for (var i = 0; i < atomes.length; i++) for (var j = i + 1; j < atomes.length; j++) {
        var dx = (atomes[i].x - atomes[j].x) * W, dy = (atomes[i].y - atomes[j].y) * H, d = Math.hypot(dx, dy);
        if (d < 150) {
          ctx.strokeStyle = "rgba(71,85,105," + (.28 * (1 - d / 150)) + ")"; ctx.lineWidth = 1.2;
          ctx.beginPath(); ctx.moveTo(atomes[i].x * W, atomes[i].y * H); ctx.lineTo(atomes[j].x * W, atomes[j].y * H); ctx.stroke();
        }
      }
      ctx.fillStyle = "rgba(20,184,166,.75)";
      atomes.forEach(function (p) { ctx.beginPath(); ctx.arc(p.x * W, p.y * H, p.r, 0, 6.2832); ctx.fill(); });
      raf = requestAnimationFrame(frame);
    }
    frame();
  }

  // ---------- interface ----------
  var CSS = "#cx{position:fixed;inset:0;z-index:2147483000;display:flex;align-items:center;justify-content:center;" +
    "font-family:Inter,system-ui,sans-serif;color:#0f172a;overflow:auto;padding:16px;background:#f8fafc}" +
    "#cx canvas,#cx video{position:fixed;inset:0;width:100%;height:100%;object-fit:cover}" +
    "#cx video{filter:blur(2px) saturate(.9);transform:scale(1.05)}" +   /* vidéo déjà bleue : pas de hue-rotate */
    "#cx .voile{position:fixed;inset:0;background:rgba(255,255,255,.45)}" +
    "@property --a{syntax:'<angle>';initial-value:0deg;inherits:false}" +
    "@keyframes cxspin{to{--a:360deg}}" +
    "#cx .carte{--mx:50%;--my:0%;position:relative;width:100%;max-width:420px;padding:32px 30px;border-radius:22px;" +
    "background:radial-gradient(380px circle at var(--mx) var(--my),rgba(255,255,255,.85),rgba(255,255,255,.5));" +
    "backdrop-filter:blur(22px) saturate(1.5);-webkit-backdrop-filter:blur(22px) saturate(1.5);" +
    "border:1px solid rgba(255,255,255,.75);box-shadow:0 20px 60px rgba(15,23,42,.25);" +
    "transition:transform .25s ease-out,box-shadow .25s}" +
    "#cx .carte:hover{box-shadow:0 28px 80px rgba(13,148,136,.3)}" +
    "#cx .carte:before,#cx .carte:after{content:'';position:absolute;inset:-2px;border-radius:24px;padding:2px;pointer-events:none;" +
    "background:conic-gradient(from var(--a),transparent 0 50%,#2dd4bf 65%,#38bdf8 80%,#6366f1 92%,transparent);" +
    "-webkit-mask:linear-gradient(#000 0 0) content-box,linear-gradient(#000 0 0);-webkit-mask-composite:xor;" +
    "mask:linear-gradient(#000 0 0) content-box exclude,linear-gradient(#000 0 0);animation:cxspin 5s linear infinite}" +
    "#cx .carte:after{inset:-4px;padding:4px;filter:blur(8px);opacity:.45}" +   /* glow léger */
    "#cx h1{margin:0;text-align:center;font-size:34px;font-weight:800;letter-spacing:-.5px;color:#0f172a}" +
    "#cx .tag{text-align:center;margin:6px 0 2px;font-size:14px;color:#1e293b}" +
    "#cx .sub{text-align:center;margin:0 0 20px;font-size:12px;color:#475569}" +
    "#cx .onglets{display:flex;background:rgba(241,245,249,.8);border-radius:12px;padding:4px;margin-bottom:18px}" +
    "#cx .onglets button{flex:1;border:0;border-radius:9px;padding:9px;font-size:14px;font-weight:600;cursor:pointer;" +
    "background:transparent;color:#64748b;transition:.2s}" +
    "#cx .onglets button:hover{color:#0f172a}" +
    "#cx .onglets button.on{background:#fff;color:#0f172a;box-shadow:0 1px 4px rgba(15,23,42,.15)}" +
    "#cx label{display:block;font-size:12px;color:#334155;margin:12px 0 5px}" +
    "#cx .champ{position:relative}" +
    "#cx input{width:100%;box-sizing:border-box;padding:11px 13px;border-radius:10px;border:1px solid #cbd5e1;" +
    "background:rgba(255,255,255,.9);color:#0f172a;font-size:14px;outline:none;transition:.2s}" +
    "#cx input:hover{border-color:#5eead4}" +
    "#cx input:focus{border-color:#0d9488;box-shadow:0 0 0 3px rgba(13,148,136,.18)}" +
    "#cx .oeil{position:absolute;right:8px;top:50%;transform:translateY(-50%);border:0;background:none;color:#64748b;" +
    "font-size:12px;cursor:pointer}" +
    "#cx .go{width:100%;margin-top:18px;padding:12px;border:0;border-radius:10px;font-size:15px;font-weight:700;color:#fff;" +
    "cursor:pointer;background:#0d9488;transition:.2s}" +
    "#cx .go:hover{background:#0f766e;transform:translateY(-2px);box-shadow:0 8px 22px rgba(13,148,136,.45)}" +
    "#cx .go:active{transform:translateY(0)}" +
    "#cx .go:disabled{opacity:.6;cursor:wait}" +
    "#cx .ou{display:flex;align-items:center;gap:10px;margin:18px 0 14px;color:#64748b;font-size:12px}" +
    "#cx .ou:before,#cx .ou:after{content:'';flex:1;height:1px;background:#cbd5e1}" +
    "#cx .goog{display:flex;align-items:center;justify-content:center;gap:10px;width:100%;box-sizing:border-box;padding:11px;" +
    "border-radius:10px;background:#fff;color:#1f2937;border:1px solid #cbd5e1;font-size:14px;font-weight:600;text-decoration:none;transition:.2s}" +
    "#cx .goog:hover{background:#f1f5f9;transform:translateY(-2px);box-shadow:0 6px 18px rgba(15,23,42,.15)}" +
    "#cx .msg{min-height:18px;margin-top:12px;font-size:13px;color:#dc2626;text-align:center}" +
    "#cx .bas{margin-top:14px;text-align:center;font-size:13px;color:#475569}" +
    "#cx .bas a{color:#0d9488;cursor:pointer;font-weight:600}" +
    "#cx .langue{position:fixed;top:14px;right:16px;z-index:2;display:flex;gap:4px}" +
    "#cx .langue button{border:1px solid #cbd5e1;background:#fff;color:#334155;border-radius:8px;" +
    "padding:5px 10px;font-size:12px;cursor:pointer;transition:.2s}" +
    "#cx .langue button:hover{transform:translateY(-1px)}" +
    "#cx .langue button.on{background:#0d9488;border-color:#0d9488;color:#fff}";

  var GLOGO = '<svg width="18" height="18" viewBox="0 0 48 48"><path fill="#EA4335" d="M24 9.5c3.5 0 6.6 1.2 9.1 3.6l6.8-6.8C35.8 2.4 30.3 0 24 0 14.6 0 6.5 5.4 2.6 13.2l7.9 6.1C12.4 13.6 17.7 9.5 24 9.5z"/><path fill="#4285F4" d="M46.5 24.5c0-1.6-.1-3.1-.4-4.5H24v9h12.7c-.6 3-2.3 5.5-4.8 7.2l7.7 6c4.5-4.2 6.9-10.3 6.9-17.7z"/><path fill="#FBBC05" d="M10.5 28.7c-.5-1.4-.8-3-.8-4.7s.3-3.2.8-4.7l-7.9-6.1C.9 16.5 0 20.1 0 24s.9 7.5 2.6 10.8l7.9-6.1z"/><path fill="#34A853" d="M24 48c6.5 0 11.9-2.1 15.9-5.8l-7.7-6c-2.1 1.4-4.9 2.3-8.2 2.3-6.3 0-11.6-4.1-13.5-9.8l-7.9 6.1C6.5 42.6 14.6 48 24 48z"/></svg>';

  function dessiner() {
    var t = T[lang], up = mode === "up";
    racine.querySelector(".contenu").innerHTML =
      '<div class="langue"><button data-l="fr" class="' + (lang === "fr" ? "on" : "") + '">FR</button>' +
      '<button data-l="en" class="' + (lang === "en" ? "on" : "") + '">EN</button></div>' +
      '<div class="carte"><h1>ChemAsk</h1><p class="tag">' + t.tag + '</p><p class="sub">' + t.sub + '</p>' +
      '<div class="onglets"><button data-m="in" class="' + (up ? "" : "on") + '">' + t.in + '</button>' +
      '<button data-m="up" class="' + (up ? "on" : "") + '">' + t.up + '</button></div>' +
      '<form novalidate><label>' + t.email + '</label><div class="champ"><input id="cx-e" type="email" autocomplete="email" placeholder="nom@exemple.com"></div>' +
      '<label>' + t.pw + '</label><div class="champ"><input id="cx-p" type="password" autocomplete="' + (up ? "new-password" : "current-password") + '">' +
      '<button type="button" class="oeil">' + t.show + '</button></div>' +
      (up ? '<label>' + t.pw2 + '</label><div class="champ"><input id="cx-p2" type="password" autocomplete="new-password"></div>' : "") +
      '<button class="go" type="submit">' + (up ? t.go_up : t.go_in) + '</button></form>' +
      '<div class="msg" id="cx-msg"></div>' +
      (google ? '<div class="ou">' + t.or + '</div><a class="goog" href="/auth/oauth/google">' + GLOGO + t.google + '</a>' : "") +
      '<div class="bas">' + (up ? t.has_acc : t.no_acc) + ' <a data-m="' + (up ? "in" : "up") + '">' + (up ? t.in : t.up) + '</a></div></div>';

    racine.querySelectorAll("[data-l]").forEach(function (b) {
      b.onclick = function () { lang = b.dataset.l; try { localStorage.setItem("chemask-lang", lang); } catch (e) {} dessiner(); };
    });
    racine.querySelectorAll("[data-m]").forEach(function (b) {
      b.onclick = function () { mode = b.dataset.m; dessiner(); };
    });
    racine.querySelector(".oeil").onclick = function (ev) {
      var champs = racine.querySelectorAll("input[type=password],input.vu");
      var cache = champs[0].type === "password";
      champs.forEach(function (c) { c.type = cache ? "text" : "password"; c.classList.toggle("vu", cache); });
      ev.target.textContent = cache ? t.hide : t.show;
    };
    racine.querySelector("form").onsubmit = envoyer;
  }

  function message(txt) { var m = document.getElementById("cx-msg"); if (m) m.textContent = txt || ""; }

  function connecter(email, mdp) {
    var corps = new URLSearchParams({ username: email, password: mdp });
    return fetch("/login", { method: "POST", body: corps, credentials: "same-origin" });
  }

  function envoyer(ev) {
    ev.preventDefault();
    var t = T[lang], up = mode === "up", bouton = racine.querySelector(".go");
    var email = document.getElementById("cx-e").value.trim().toLowerCase();
    var mdp = document.getElementById("cx-p").value;
    message("");
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]{2,}$/.test(email)) return message(t.e_email);
    if (up && mdp.length < 6) return message(t.e_password);
    if (up && mdp !== document.getElementById("cx-p2").value) return message(t.e_match);
    bouton.disabled = true;
    var etape = up
      ? fetch("/register", { method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email: email, password: mdp }) })
          .then(function (r) {
            if (r.ok) return connecter(email, mdp);
            return r.json().then(function (j) { throw new Error("e_" + j.error); });
          })
      : connecter(email, mdp);
    etape.then(function (r) {
      if (r.ok) { location.href = "/"; return; }
      throw new Error("e_bad");
    }).catch(function (e) {
      bouton.disabled = false;
      var k = String(e.message || "");
      message(t[k] || t.e_net);
    });
  }

  function monter() {
    if (racine) return;
    racine = document.createElement("div");
    racine.id = "cx";
    racine.innerHTML = "<style>" + CSS + "</style><canvas></canvas>" +
      "<video autoplay muted loop playsinline src='/public/fond.mp4?v=3'></video><div class='voile'></div>" +
      "<div class='contenu' style='position:relative;width:100%;display:flex;justify-content:center'></div>";
    document.body.appendChild(racine);
    document.body.style.overflow = "hidden";
    fond(racine.querySelector("canvas"));
    var v = racine.querySelector("video");  // pas de fichier fond.mp4 : on garde le fond de secours
    v.onerror = function () { v.remove(); };
    v.addEventListener("error", function () { v.remove(); }, true);
    var lent = function () { v.playbackRate = 0.5; };  // vidéo ralentie (0.5 = 2x plus lente)
    v.addEventListener("loadedmetadata", lent); v.addEventListener("play", lent); lent();
    racine.addEventListener("mousemove", function (e) {  // reflet de lumière + légère inclinaison 3D
      var c = racine.querySelector(".carte");
      if (!c) return;
      var r = c.getBoundingClientRect(), x = e.clientX - r.left, y = e.clientY - r.top;
      c.style.setProperty("--mx", x + "px"); c.style.setProperty("--my", y + "px");
      var rx = ((y / r.height) - .5) * -5, ry = ((x / r.width) - .5) * 5;
      c.style.transform = "perspective(900px) rotateX(" + rx.toFixed(2) + "deg) rotateY(" + ry.toFixed(2) + "deg)";
    });
    racine.addEventListener("mouseleave", function () {
      var c = racine.querySelector(".carte"); if (c) c.style.transform = "";
    });
    dessiner();
    fetch("/auth/config").then(function (r) { return r.json(); }).then(function (c) {
      if ((c.oauthProviders || []).indexOf("google") >= 0) { google = true; dessiner(); }
    }).catch(function () {});
  }
  function demonter() {
    if (!racine) return;
    cancelAnimationFrame(raf); racine.remove(); racine = null; document.body.style.overflow = "";
  }
  setInterval(function () { (location.pathname.replace(/\/$/, "") === "/login" ? monter : demonter)(); }, 300);
})();