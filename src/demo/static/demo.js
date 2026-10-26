/* Progressive enhancement only: pages work as server-rendered HTML; this adds form submission, availability counts and polling. No external requests. */
(function () {
  "use strict";
  var page = document.body.getAttribute("data-page");
  function $(s, r) { return (r || document).querySelector(s); }
  function $$(s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); }
  function show(el, msg) { if (!el) return; el.textContent = msg; el.classList.remove("hidden"); }
  function post(url, body) {
    return fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body || {}) })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, status: r.status, body: j }; }); });
  }

  // ------------------------------------------------------------------ preferences (this browser only)
  var PREF_KEY = "smart_prefs";
  function prefs() { try { return JSON.parse(localStorage.getItem(PREF_KEY) || "{}") || {}; } catch (e) { return {}; } }
  function savePrefs(p) { try { localStorage.setItem(PREF_KEY, JSON.stringify(p)); return true; } catch (e) { return false; } }
  function fmt(sec) { sec = Math.max(0, Math.floor(sec)); var h = Math.floor(sec / 3600), m = Math.floor(sec % 3600 / 60), s = sec % 60; return (h ? h + ":" + (m < 10 ? "0" : "") : "") + m + ":" + (s < 10 ? "0" : "") + s; }

  // ------------------------------------------------------------------ setup
  function initSetup() {
    var cards = $$(".role-card"), jd = $("#jd"), cnt = $("#jd-count"), form = $("#setup-form"), btn = $("#start-btn"), note = $("#start-note"), max = jd ? parseInt(jd.getAttribute("maxlength"), 10) : 4000;
    function current() { var c = cards.filter(function (x) { return x.getAttribute("aria-checked") === "true"; })[0]; return c || null; }
    function plan() {
      var c = current(), pr = $("#plan-problem"), pt = $("#plan-topics");
      if (c) { var ds = JSON.parse(c.getAttribute("data-domains") || "[]"); $("#plan-role").textContent = "Topics for " + c.getAttribute("data-role") + ": " + ds.join(", ") + "."; pr.classList.add("hidden"); }
      else { $("#plan-role").textContent = ""; pr.textContent = "Choose a role."; pr.classList.remove("hidden"); }
      btn.disabled = !c;
    }
    function select(c) { cards.forEach(function (x) { x.setAttribute("aria-checked", String(x === c)); }); plan(); }
    cards.forEach(function (c, i) {
      c.addEventListener("click", function () { select(c); });
      c.addEventListener("keydown", function (e) {                  // arrow keys move between options like a radio group
        var k = e.key === "ArrowRight" || e.key === "ArrowDown" ? 1 : e.key === "ArrowLeft" || e.key === "ArrowUp" ? -1 : 0;
        if (!k) return; e.preventDefault(); var n = cards[(i + k + cards.length) % cards.length]; n.focus(); n.click();
      });
    });
    try { var want = new URLSearchParams(window.location.search).get("role"); var m = cards.filter(function (x) { return x.getAttribute("data-role") === want; })[0]; if (m) select(m); } catch (e) {}
    if (jd) jd.addEventListener("input", function () { cnt.textContent = jd.value.length + " / " + max; });
    plan();
    form.addEventListener("submit", function (ev) {
      ev.preventDefault();
      var c = current(); if (!c) { show($("#form-error"), "Choose a role first."); return; }
      $("#form-error").classList.add("hidden");
      var body = { role: c.getAttribute("data-role") };
      if (jd && jd.value.trim()) body.job_description = jd.value;
      var ty = document.querySelector("input[name=interview_type]:checked"); if (ty && ty.value !== "technical") body.interview_type = ty.value;
      var tb = document.querySelector("input[name=time_budget_min]:checked"); if (tb) body.time_budget_min = parseInt(tb.value, 10);
      var mm = prefs().modular; if (mm && mm !== "off") body.modular_mode = mm;
      var fm = prefs().followup; if (fm && fm !== "deterministic") body.followup_mode = fm;
      btn.disabled = true; note.innerHTML = '<span class="spinner" aria-hidden="true"></span>Planning your interview… (the first start after launching the server loads the models and can take a little while)';
      post("/demo/api/sessions", body).then(function (r) {
        if (r.ok) { try { localStorage.setItem("smart_last_sid", r.body.session_id); } catch (e) {} window.location.href = r.body.url; return; }
        show($("#form-error"), r.body.error || "Could not start the interview."); btn.disabled = false; note.textContent = "";
      }).catch(function () { show($("#form-error"), "The server could not be reached."); btn.disabled = false; note.textContent = ""; });
    });
  }

  function initResume() {
    var sid = null; try { sid = localStorage.getItem("smart_last_sid"); } catch (e) {}
    if (!sid) return;
    fetch("/demo/api/sessions/" + encodeURIComponent(sid)).then(function (r) { return r.ok ? r.json() : null; }).then(function (j) {
      var box = $("#resume"); if (!j || !box) return;
      var a = document.createElement("a"); a.className = "btn primary";
      if (j.error) return;
      if (j.status === "active") { a.href = "/demo/s/" + sid; a.textContent = "Continue"; box.innerHTML = "<strong>You have an unfinished interview</strong> <span class='muted'>(question " + j.current + " of " + j.total + ")</span> "; }
      else { a.href = "/demo/s/" + sid + "/summary"; a.textContent = "View summary"; box.innerHTML = "<strong>Your last interview is finished</strong> "; }
      box.appendChild(a); box.classList.remove("hidden");
    }).catch(function () {});
  }

  // ------------------------------------------------------------------ polling a pending experimental result
  function poll(slot, sid, n) {
    var tries = 0;
    (function tick() {
      tries++;
      fetch("/demo/api/sessions/" + sid + "/answers/" + n + (page === "summary" ? "?compact=1" : "")).then(function (r) { return r.json(); }).then(function (j) {
        if (j.html) slot.innerHTML = j.html;
        if (j.pending && tries < 180) setTimeout(tick, 2500); else { var pb = $("#pending-banner"); if (pb && !$("[data-poll]")) pb.classList.add("hidden"); }
      }).catch(function () { if (tries < 180) setTimeout(tick, 5000); });
    })();
  }

  // ------------------------------------------------------------------ interview (a conversation: the next interviewer message is rendered by the server and appended)
  function initInterview() {
    var root = $("#interview"), sid = root.getAttribute("data-sid"), n = parseInt(root.getAttribute("data-n"), 10), isCode = root.getAttribute("data-code") === "1";
    var form = $("#answer-form"), ta = $("#answer"), err = $("#answer-error"), counter = $("#counter"), submit = $("#submit-btn"), thread = $("#thread"), thinking = $("#thinking"), gut = $("#gutter");
    var calm = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    ta.focus({ preventScroll: true });
    var dnote = $("#draft-note");
    function dkey() { return "smart_draft:" + sid + ":" + n; }
    function gutter() { if (!gut || gut.hidden) return; var k = ta.value.split("\n").length, out = []; for (var i = 1; i <= k; i++) out.push(i); gut.textContent = out.join("\n"); gut.scrollTop = ta.scrollTop; }
    function saveDraft() { try { if (ta.value) sessionStorage.setItem(dkey(), ta.value); else sessionStorage.removeItem(dkey()); if (dnote) dnote.textContent = ta.value ? "Draft kept in this tab" : ""; } catch (e) {} }
    function clearDraft() { try { sessionStorage.removeItem(dkey()); } catch (e) {} }
    try { var d0 = sessionStorage.getItem(dkey()); if (d0 && !ta.value) { ta.value = d0; if (dnote) dnote.textContent = "Draft restored"; } } catch (e) {}
    ta.addEventListener("input", function () { counter.textContent = ta.value.length + " / 8000"; saveDraft(); gutter(); });
    ta.addEventListener("scroll", function () { if (gut) gut.scrollTop = ta.scrollTop; });
    counter.textContent = ta.value.length + " / 8000"; gutter();
    function reveal(el) { if (el && el.scrollIntoView) el.scrollIntoView({ block: "nearest", behavior: calm ? "auto" : "smooth" }); }
    // timers: counted from server-supplied elapsed time, so a refresh does not reset them
    var t0 = Date.now(), e0 = parseInt(root.getAttribute("data-elapsed") || "0", 10), s0n = parseInt(root.getAttribute("data-spent") || "0", 10);
    var tq = $("#t-q"), ta2 = $("#t-all"), tb = $("#t-toggle"), timerOn = prefs().timer !== false, stopped = false;
    function elapsed() { return e0 + (Date.now() - t0) / 1000; }
    function tick() { if (stopped) return; var el = elapsed(); tq.textContent = fmt(el); ta2.textContent = fmt(s0n + Math.min(el, 1800)); }
    function applyTimer() { tq.parentNode.classList.toggle("hidden", !timerOn); ta2.parentNode.classList.toggle("hidden", !timerOn); tb.textContent = timerOn ? "Hide timer" : "Show timer"; tb.setAttribute("aria-pressed", String(!timerOn)); }
    tb.addEventListener("click", function () { timerOn = !timerOn; var p = prefs(); p.timer = timerOn; savePrefs(p); applyTimer(); });
    applyTimer(); tick(); setInterval(tick, 1000);
    // editor mode: plain text for conversation answers, a Python editor for code questions
    var tabmode = $("#tabmode"), escaped = false, IND = "    ";
    function setMode(code) {
      isCode = code; root.setAttribute("data-code", code ? "1" : "0"); $("#composer").classList.toggle("is-code", code);
      ta.setAttribute("data-code", code ? "1" : "0"); ta.classList.toggle("codearea", code); ta.rows = code ? 14 : 6; var eb = $(".ed-bar"); if (eb) eb.hidden = !code;
      ta.setAttribute("spellcheck", code ? "false" : "true"); ta.setAttribute("autocapitalize", code ? "off" : "sentences");
      if (code) ta.setAttribute("wrap", "off"); else ta.removeAttribute("wrap");
      ta.placeholder = code ? "Write your Python here" : "Reply in your own words. Short, specific answers are fine.";
      $("#ed-name").textContent = code ? "answer.py" : "answer.txt"; $("#ed-lang").innerHTML = code ? '<span class="lang">Python</span>' : "Plain text";
      $("#answer-label").textContent = code ? "Your code" : "Your answer";
      if (gut) gut.hidden = !code; $$(".only-code").forEach(function (e) { e.hidden = !code; }); if (tabmode) tabmode.checked = code; gutter();
    }
    function edit(start, end, text, selStart, selEnd) {      // keep the browser's undo stack when possible
      ta.focus(); ta.setSelectionRange(start, end);
      var ok = false; try { ok = document.execCommand("insertText", false, text); } catch (x) {}
      if (!ok) { ta.setRangeText(text, start, end, "end"); ta.dispatchEvent(new Event("input")); }
      ta.setSelectionRange(selStart, selEnd);
    }
    ta.addEventListener("keydown", function (e) {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") { e.preventDefault(); form.requestSubmit(); return; }
      if (e.key === "Escape") { escaped = true; return; }
      if (!tabmode || !tabmode.checked) return;
      var v = ta.value, s0 = ta.selectionStart, e1 = ta.selectionEnd;
      if (e.key === "Tab") {
        if (escaped && !e.shiftKey) { escaped = false; return; }   // Esc then Tab leaves the box (keyboard users are never trapped)
        e.preventDefault();
        var ls = v.lastIndexOf("\n", s0 - 1) + 1;
        if (s0 === e1 && !e.shiftKey) { var col = s0 - ls; var add = IND.slice(col % 4); edit(s0, e1, add, s0 + add.length, s0 + add.length); return; }
        var le = e1; if (le > s0 && v.charAt(le - 1) === "\n") le--; var le2 = v.indexOf("\n", le); if (le2 < 0) le2 = v.length;
        var block = v.slice(ls, le2), lines = block.split("\n"), out;
        if (e.shiftKey) { out = lines.map(function (l) { return l.replace(/^( {1,4}|\t)/, ""); }); }
        else { out = lines.map(function (l) { return IND + l; }); }
        var nb = out.join("\n"), delta0 = (out[0].length - lines[0].length);
        edit(ls, le2, nb, Math.max(ls, s0 + delta0), e1 + (nb.length - block.length));
        return;
      }
      escaped = false;
      if (e.key === "Enter" && !e.shiftKey && !e.ctrlKey && !e.metaKey && s0 === e1) {   // keep the current line's indentation; one level deeper after a colon
        var ls2 = v.lastIndexOf("\n", s0 - 1) + 1, line = v.slice(ls2, s0), m = /^[ \t]*/.exec(line)[0];
        if (!m && !/:\s*$/.test(line)) return;
        e.preventDefault(); var extra = /:\s*$/.test(line) ? IND : ""; var ins = "\n" + m + extra; edit(s0, e1, ins, s0 + ins.length, s0 + ins.length);
      }
    });
    // conversation helpers
    function yourBubble(text, skipped, code) {
      var art = document.createElement("article"); art.className = "turn turn-you"; art.setAttribute("data-n", String(n));
      var b = document.createElement("div"); b.className = "bubble"; var w = document.createElement("p"); w.className = "who"; w.textContent = "You"; b.appendChild(w);
      if (skipped) { var p = document.createElement("p"); p.className = "muted"; p.textContent = "Skipped"; b.appendChild(p); }
      else if (code) { var cb = document.createElement("div"); cb.className = "codeblock"; var pre = document.createElement("pre"); pre.className = "code"; var c = document.createElement("code"); c.textContent = text; pre.appendChild(c); cb.appendChild(pre); b.appendChild(cb); }
      else { var d = document.createElement("div"); d.className = "answer-view"; var pa = document.createElement("div"); pa.className = "prose-answer"; pa.textContent = text; d.appendChild(pa); b.appendChild(d); }
      art.appendChild(b); thread.insertBefore(art, thinking); return art;
    }
    function demote() { var cur = $(".turn-ai.is-current", thread); if (cur) { cur.classList.remove("is-current"); cur.removeAttribute("aria-labelledby"); var q = $("#qtext", cur); if (q) q.removeAttribute("id"); } }
    function appendPrompt(html) { var t = document.createElement("template"); t.innerHTML = html.trim(); var node = t.content.firstElementChild; thread.insertBefore(node, thinking); return node; }
    function lock(on) { $$("button", form).forEach(function (b) { b.disabled = on; }); ta.readOnly = on; }
    var thinkTimer = 0;
    var slowTimer = 0;
    function think(on) {                                   // shown only while the server is actually working on the answer (a quick reply never flashes it)
      clearTimeout(thinkTimer); clearTimeout(slowTimer);
      var lab = $("#think-label"), root = $("#interview");
      if (lab) lab.textContent = "";
      if (!on) { thinking.classList.add("hidden"); thinking.setAttribute("aria-hidden", "true"); return; }
      var fu = root && root.getAttribute("data-fu-mode") !== "deterministic" && root.getAttribute("data-stage") === "core";     // an experimental follow-up may be prepared after this answer
      thinkTimer = setTimeout(function () { thinking.classList.remove("hidden"); thinking.setAttribute("aria-hidden", "false"); if (lab && fu) lab.textContent = "Preparing a follow-up…"; reveal(thinking); }, 250);
      if (fu) slowTimer = setTimeout(function () { if (lab) lab.textContent = "Still preparing. If this takes too long a standard follow-up is used."; }, 7000);
    }
    function applyNext(body, label) {
      var tr = $("#tracker"); if (tr && body.tracker_html) tr.innerHTML = body.tracker_html;
      if (body.progress) { var pg = $("#prog"); pg.max = body.progress.total; pg.value = body.progress.done; var pf = $("#pb-fill"); if (pf) pf.setAttribute("width", String(body.progress.total ? Math.min(100, 100 * (body.progress.done + (body.finished ? 0 : 1)) / body.progress.total) : 0)); }
      demote(); var node = appendPrompt(body.next_html);
      if (body.finished) {
        stopped = true; $("#composer").classList.add("hidden"); $("#stage-label").textContent = "Wrap-up"; $("#finish-btn").classList.add("hidden"); reveal(node);
        var fb = $("#see-feedback"); if (fb) fb.focus({ preventScroll: true });
        return;
      }
      n = body.next.n; root.setAttribute("data-n", String(n)); root.setAttribute("data-stage", body.next.stage); root.setAttribute("data-total", String(body.next.total)); $("#stage-label").textContent = body.next.stage_label || "";
      setMode(!!body.next.code); ta.value = ""; counter.textContent = "0 / 8000"; if (dnote) dnote.textContent = ""; gutter();
      s0n += Math.min(elapsed(), 1800); e0 = 0; t0 = Date.now(); stopped = false; tick();
      lock(false); submit.textContent = "Send answer"; ta.focus({ preventScroll: true }); reveal(node);
    }
    function fail(r, mine, skipping) {
      think(false); if (mine && mine.parentNode) mine.parentNode.removeChild(mine); stopped = false; lock(false); submit.textContent = "Send answer";
      if (r && r.status === 404) { show(err, ((r.body && r.body.error) || "This interview is no longer available.") + " Start a new interview from the home page."); return; }
      if (r && r.status === 409 && r.body && (r.body.finished || r.body.current)) { show(err, ((r.body.error) || "This question was already handled.") + " Taking you to where you left off…"); setTimeout(function () { window.location.href = r.body.finished ? "/demo/s/" + sid + "/summary" : "/demo/s/" + sid; }, 1400); return; }
      show(err, (r && r.body && r.body.error) || (skipping ? "Could not skip." : "The server could not be reached. Your answer is still in the box; try again (it will not be counted twice)."));
    }
    form.addEventListener("submit", function (ev) {
      ev.preventDefault(); err.classList.add("hidden");
      if (!ta.value.trim()) { show(err, "Write an answer first, or use Skip."); return; }
      var text = ta.value, mine = yourBubble(text, false, isCode); reveal(mine);
      lock(true); submit.textContent = "Sending…"; stopped = true; think(true);
      post("/demo/api/sessions/" + sid + "/answer", { n: n, answer: text }).then(function (r) {
        if (!r.ok) { fail(r, mine, false); return; }
        think(false); clearDraft(); applyNext(r.body);
      }).catch(function () { fail(null, mine, false); });
    });
    $("#skip-btn").addEventListener("click", function () {
      err.classList.add("hidden"); var mine = yourBubble("", true, false); lock(true); stopped = true; think(true);
      post("/demo/api/sessions/" + sid + "/skip", { n: n }).then(function (r) {
        if (!r.ok) { fail(r, mine, true); return; }
        think(false); clearDraft(); applyNext(r.body);
      }).catch(function () { fail(null, mine, true); });
    });
    var armed = false, fbtn = $("#finish-btn");
    fbtn.addEventListener("click", function () {                      // two-step confirmation without a browser dialog
      if (!armed) { armed = true; fbtn.textContent = "Click again to end now"; setTimeout(function () { armed = false; fbtn.textContent = "End interview"; }, 6000); return; }
      post("/demo/api/sessions/" + sid + "/finish", {}).then(function (r) { if (r.ok) window.location.href = r.body.next_url; });
    });
  }

  // ------------------------------------------------------------------ summary
  function initSummary() {
    var root = $("#summary"), sid = root.getAttribute("data-sid");
    var fb = $("#finish-btn"); if (fb) fb.addEventListener("click", function () { post("/demo/api/sessions/" + sid + "/finish", {}).then(function () { window.location.reload(); }); });
    var del = $("#delete-btn");
    if (del) { var armed = false; del.addEventListener("click", function () {
      if (!armed) { armed = true; del.textContent = "Click again to delete permanently"; setTimeout(function () { armed = false; del.textContent = "Delete this interview's data"; }, 6000); return; }
      post("/demo/api/sessions/" + sid + "/delete", {}).then(function (r) { try { if (localStorage.getItem("smart_last_sid") === sid) localStorage.removeItem("smart_last_sid"); } catch (e) {} window.location.href = (r.body && r.body.next_url) || "/demo/"; });
    }); }
    $$(".eval-slot").forEach(function (slot) { if ($("[data-poll]", slot)) poll(slot, sid, slot.getAttribute("data-n")); });
  }

  function initSettings() {
    $("#prefs-form").addEventListener("submit", function (ev) { ev.preventDefault(); });
    var p = prefs();
    var pm = $("#pref-modular"); if (pm && p.modular && $$("option", pm).some(function (o) { return o.value === p.modular; })) pm.value = p.modular;
    var pf = $("#pref-followup"); if (pf && p.followup && $$("option", pf).some(function (o) { return o.value === p.followup; })) pf.value = p.followup;
    $("#pref-timer").checked = p.timer !== false;
    $("#prefs-save").addEventListener("click", function () {
      var q = prefs(); q.modular = pm ? pm.value : "off"; q.followup = pf ? pf.value : "deterministic"; q.timer = $("#pref-timer").checked; var ok = savePrefs(q);
      var s = $("#prefs-saved"); s.textContent = ok ? "Saved" : "Could not save in this browser"; s.classList.remove("hidden"); setTimeout(function () { s.classList.add("hidden"); }, 2500);
    });
    var er = $("#erase-all"); if (!er) return; var armed = false;
    er.addEventListener("click", function () {
      if (!armed) { armed = true; er.textContent = "Click again to delete everything"; setTimeout(function () { armed = false; er.textContent = "Delete all saved interviews"; }, 6000); return; }
      post("/demo/api/sessions/delete-all", {}).then(function (r) {
        try { localStorage.removeItem("smart_last_sid"); } catch (e) {}
        $("#erase-note").textContent = r.ok ? " Deleted " + r.body.deleted + " interview(s)." : " " + (r.body.error || "Could not delete.");
        er.textContent = "Delete all saved interviews"; armed = false;
      });
    });
  }

  // ------------------------------------------------------------------ motion: pointer tilt (dashboard and setup cards only; never on the interview screen)
  // ------------------------------------------------------------------ navigation indicator (slides under the hovered or current item; never needed for use)
  function initNav() {
    var nav = $("#mainnav"), ind = nav && $(".nav-ind", nav); if (!nav || !ind) return;
    var links = $$("a", nav), cur = $("a[aria-current=page]", nav);
    function to(a) {
      if (!a) return;
      ind.style.setProperty("width", a.offsetWidth + "px"); ind.style.setProperty("transform", "translateX(" + a.offsetLeft + "px)");
    }
    function rest() { if (cur) { to(cur); nav.classList.add("ready"); } else nav.classList.remove("ready"); }
    links.forEach(function (a) { a.addEventListener("pointerenter", function () { nav.classList.add("ready"); to(a); }); a.addEventListener("focus", function () { nav.classList.add("ready"); to(a); }); });
    nav.addEventListener("pointerleave", rest); nav.addEventListener("focusout", function (e) { if (!nav.contains(e.relatedTarget)) rest(); });
    window.addEventListener("resize", rest); rest();
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(rest);
  }

  // ------------------------------------------------------------------ home: quick start (one click) and the hero preview
  function initHome() {
    var grid = $("#qs-grid"), calm = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (grid) {
      var busy = false;
      $$("[data-start-role]", grid).forEach(function (card) {
        card.addEventListener("click", function (ev) {
          if (ev.ctrlKey || ev.metaKey || ev.shiftKey || ev.button) return;      // let "open in new tab" work like a normal link
          ev.preventDefault(); if (busy) return; busy = true;
          var err = $("#qs-error"); err.classList.add("hidden");
          card.setAttribute("aria-busy", "true"); $$(".qs", grid).forEach(function (c) { if (c !== card) c.classList.add("dim"); });
          var go = $(".go", card), old = go.innerHTML; go.innerHTML = '<span class="spinner" aria-hidden="true"></span>Preparing…';
          function undo(msg) { busy = false; card.removeAttribute("aria-busy"); $$(".qs", grid).forEach(function (c) { c.classList.remove("dim"); }); go.innerHTML = old; show(err, msg); err.scrollIntoView({ block: "nearest" }); }
          post("/demo/api/sessions", Object.assign({ role: card.getAttribute("data-start-role") }, (prefs().modular && prefs().modular !== "off") ? { modular_mode: prefs().modular } : {}, (prefs().followup && prefs().followup !== "deterministic") ? { followup_mode: prefs().followup } : {})).then(function (r) {
            if (r.ok) { try { localStorage.setItem("smart_last_sid", r.body.session_id); } catch (e) {} window.location.href = r.body.url; return; }
            undo((r.body && r.body.error) || "Could not start the interview. Try the full setup page.");
          }).catch(function () { undo("The server could not be reached."); });
        });
        card.addEventListener("pointermove", function (e) { var r = card.getBoundingClientRect(); card.style.setProperty("--mx", ((e.clientX - r.left) / r.width * 100).toFixed(0) + "%"); });
      });
    }
    var typed = $("#typed");                                                    // decorative preview: types the sample answer once, then stays
    if (typed && !calm) {
      var full = typed.getAttribute("data-text"), i = 0; typed.textContent = "";
      setTimeout(function () { var iv = setInterval(function () { i += 2; typed.textContent = full.slice(0, i); if (i >= full.length) { clearInterval(iv); typed.textContent = full; } }, 28); }, 900);
    }
  }

  function initMotion() {
    var calm = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    var fine = window.matchMedia && window.matchMedia("(hover: hover) and (pointer: fine)").matches;
    if (calm || !fine || page === "interview") return;
    function tilt(el, max) {
      var raf = 0, rx = 0, ry = 0;
      function apply() { raf = 0; el.style.setProperty("--rx", rx.toFixed(2) + "deg"); el.style.setProperty("--ry", ry.toFixed(2) + "deg"); }
      el.addEventListener("pointermove", function (e) {
        var r = el.getBoundingClientRect(), px = (e.clientX - r.left) / r.width - 0.5, py = (e.clientY - r.top) / r.height - 0.5;
        ry = px * max * 2; rx = -py * max * 2; el.classList.add("tilting"); if (!raf) raf = requestAnimationFrame(apply);
      });
      el.addEventListener("pointerleave", function () { rx = ry = 0; el.classList.remove("tilting"); if (!raf) raf = requestAnimationFrame(apply); });
    }
    $$("[data-tilt]").forEach(function (el) { tilt(el, 2.5); });
    var st = $("[data-stage]"), win = st && $("[data-win]", st);               // hero preview: the window tilts and the floating labels drift at different depths
    if (st && win) {
      var raf = 0, px = 0, py = 0;
      function apply() { raf = 0; win.style.setProperty("--ry", (-9 + px * 16).toFixed(2) + "deg"); win.style.setProperty("--rx", (4 - py * 12).toFixed(2) + "deg"); $$(".float", st).forEach(function (f) { f.style.setProperty("--px", px.toFixed(3)); f.style.setProperty("--py", py.toFixed(3)); }); }
      st.addEventListener("pointermove", function (e) { var r = st.getBoundingClientRect(); px = (e.clientX - r.left) / r.width - 0.5; py = (e.clientY - r.top) / r.height - 0.5; win.classList.add("tilting"); if (!raf) raf = requestAnimationFrame(apply); });
      st.addEventListener("pointerleave", function () { px = py = 0; win.classList.remove("tilting"); if (!raf) raf = requestAnimationFrame(apply); });
    }
  }
  initNav();
  initMotion();

  window.addEventListener("pageshow", function (e) { if (e.persisted && (page === "interview" || page === "summary")) window.location.reload(); });   // back/forward cache: never show a stale question
  if (page === "setup" && $("#setup-form")) initSetup();
  if (page === "dashboard") { initResume(); initHome(); }
  if (page === "settings") initSettings();
  if (page === "interview") initInterview();
  if (page === "summary") initSummary();
})();
