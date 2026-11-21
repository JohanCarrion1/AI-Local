"use strict";
const $ = (id) => document.getElementById(id);
const command = (action, data = {}) => {
  if (window.Native) Native.command(action, JSON.stringify(data));
};
function readJSON(key, fallback) {
  try {
    return JSON.parse(localStorage.getItem(key) || "null") || fallback;
  } catch (_) {
    return fallback;
  }
}
const defaultPrefs = {
  name: "",
  accent: "#e5a078",
  mode: "dark",
  defaultModel: "",
  autoLoad: false,
  context: 1024,
  response: 512,
  instructions: "Eres un asistente útil. Responde en español con precisión.",
  showStats: false,
};
let prefs = { ...defaultPrefs, ...readJSON("preferences.v1", {}) };
if (!/^#[0-9a-f]{6}$/i.test(prefs.accent)) prefs.accent = defaultPrefs.accent;
if (!["dark", "light", "system"].includes(prefs.mode)) prefs.mode = "dark";
if (![512, 1024, 2048, 4096].includes(Number(prefs.context)))
  prefs.context = 1024;
if (![256, 512, 1024, 2048].includes(Number(prefs.response)))
  prefs.response = 512;
prefs.name = String(prefs.name || "").slice(0, 40);
prefs.instructions = String(
  prefs.instructions || defaultPrefs.instructions,
).slice(0, 4000);
let store = readJSON("conversations.v1", { currentId: "", sessions: [] });
if (!Array.isArray(store.sessions)) store = { currentId: "", sessions: [] };
store.sessions = store.sessions
  .filter((s) => s && typeof s.id === "string" && Array.isArray(s.messages))
  .map((s) => ({
    ...s,
    title: typeof s.title === "string" ? s.title : "Conversación guardada",
    messages: s.messages.filter(
      (m) =>
        m &&
        ["user", "assistant"].includes(m.role) &&
        typeof m.content === "string",
    ),
  }));
if (!store.sessions.length) {
  const legacy = readJSON("chat", []);
  if (Array.isArray(legacy) && legacy.length)
    store.sessions.push({
      id: makeId(),
      title: "Conversación guardada",
      modelId: localStorage.getItem("chatModel") || "",
      messages: legacy,
      updatedAt: Date.now(),
    });
}
function makeId() {
  return (
    globalThis.crypto?.randomUUID?.() ||
    Date.now().toString(36) + "-" + Math.random().toString(36).slice(2)
  );
}
function blankSession() {
  return {
    id: makeId(),
    title: "Nuevo chat",
    modelId: "",
    messages: [],
    updatedAt: Date.now(),
  };
}
if (!store.sessions.length) store.sessions.push(blankSession());
let current =
  store.sessions.find((s) => s.id === store.currentId) || store.sessions[0];
store.currentId = current.id;
let messages = current.messages,
  conversationModel = current.modelId || "";
let state = { models: [], installed: [], ram: 0, available: 0 },
  filter = "powerful",
  running = false,
  operationKind = null,
  loadingModelId = "",
  attachment = false,
  answer = "",
  fileSha = "",
  opened = null,
  pending = null,
  currentPage = "chat",
  drawerOpen = false,
  nativeSystemDark = null,
  autoLoadAttempted = false;
let operationStatus = "",
  operationStarted = 0,
  busyTimer = null,
  chatFailure = current.failure || null,
  operationStopped = false;
let resumeAfterLoad = false;
let recoveringPending = !!current.pending,
  loadRequestId = "";
const handledNativeJobs = new Set();
let nativeInstance = "",
  nativeRevision = -1,
  latestInference = null;
const downloads = new Map();
$("contextTokens").value = String(prefs.context);
$("responseTokens").value = String(prefs.response);
function savePrefs() {
  try {
    localStorage.setItem("preferences.v1", JSON.stringify(prefs));
    $("settingsStatus").textContent = "Guardado en este teléfono.";
    return true;
  } catch (_) {
    $("settingsStatus").textContent =
      "No se pudieron guardar los ajustes. Revisa el espacio disponible.";
    return false;
  }
}
function saveConversations() {
  try {
    store.currentId = current.id;
    localStorage.setItem("conversations.v1", JSON.stringify(store));
    localStorage.setItem("chat", JSON.stringify(messages));
    localStorage.setItem("chatModel", conversationModel);
  } catch (_) {
    toast(
      "No se pudo guardar el historial. Revisa el almacenamiento del teléfono.",
      true,
    );
  }
}
function persist() {
  current.messages = messages;
  current.modelId = conversationModel;
  current.title =
    messages
      .find((m) => m.role === "user")
      ?.content.replace(/\s+/g, " ")
      .trim()
      .slice(0, 64) || "Nuevo chat";
  current.updatedAt = Date.now();
  saveConversations();
  renderHistory();
}
function page(id) {
  if (!["chat", "library", "github"].includes(id)) return;
  currentPage = id;
  closeDrawer();
  if ($("settings").open) $("settings").close();
  if ($("modelPicker").open) $("modelPicker").close();
  document
    .querySelectorAll(".page")
    .forEach((p) => p.classList.toggle("hidden", p.id !== id));
  document
    .querySelectorAll("[data-page]")
    .forEach((b) => b.classList.toggle("current", b.dataset.page === id));
  $("app").dataset.page = id;
  updateHeader();
  if (id === "chat") renderChat();
}
function openDrawer() {
  $("drawer").classList.remove("hidden");
  $("drawerBackdrop").classList.remove("hidden");
  $("app").inert = true;
  drawerOpen = true;
  $("menuToggle").setAttribute("aria-expanded", "true");
  renderHistory();
  $("closeDrawer").focus();
}
function closeDrawer() {
  if (!drawerOpen) return;
  $("drawer").classList.add("hidden");
  $("drawerBackdrop").classList.add("hidden");
  $("app").inert = false;
  drawerOpen = false;
  $("menuToggle").setAttribute("aria-expanded", "false");
  $("menuToggle").focus();
}
$("menuToggle").onclick = openDrawer;
$("closeDrawer").onclick = closeDrawer;
$("drawerBackdrop").onclick = closeDrawer;
document.querySelectorAll("[data-page]").forEach(
  (b) =>
    (b.onclick = () => {
      page(b.dataset.page);
      if (b.dataset.page === "chat" && !state.active && prefs.defaultModel)
        loadDefault();
    }),
);
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && drawerOpen) {
    event.preventDefault();
    closeDrawer();
  }
  if (event.key === "Tab" && drawerOpen) {
    const controls = [
      ...$("drawer").querySelectorAll("button:not(:disabled),input"),
    ];
    const first = controls[0],
      last = controls.at(-1);
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }
});
window.handleBack = () => {
  for (const id of ["confirm", "modelPicker", "settings"])
    if ($(id).open) {
      if (id === "modelPicker") resumeAfterLoad = false;
      $(id).close();
      return true;
    }
  if (drawerOpen) {
    closeDrawer();
    return true;
  }
  if (currentPage !== "chat") {
    page("chat");
    return true;
  }
  return false;
};
function renderHistory() {
  const root = $("chatHistory"),
    query = $("historySearch").value.trim().toLocaleLowerCase("es");
  root.replaceChildren();
  const items = store.sessions
    .slice()
    .sort((a, b) => b.updatedAt - a.updatedAt)
    .filter((s) => s.title.toLocaleLowerCase("es").includes(query));
  for (const session of items) {
    const b = el(
      "button",
      "history-item" + (session.id === current.id ? " selected" : ""),
    );
    b.append(el("span", "history-icon", "◌"), el("span", "", session.title));
    b.disabled = running;
    b.onclick = () => switchSession(session.id);
    root.append(b);
  }
  if (!items.length)
    root.append(
      el("small", "history-empty", "No hay conversaciones que coincidan."),
    );
}
$("historySearch").oninput = renderHistory;
function switchSession(id) {
  if (running)
    return toast("Detén la respuesta antes de cambiar de conversación.");
  const next = store.sessions.find((s) => s.id === id);
  if (!next) return;
  current = next;
  resumeAfterLoad = false;
  messages = current.messages;
  conversationModel = current.modelId || "";
  answer = "";
  chatFailure = current.failure || null;
  command("clearImage");
  saveConversations();
  renderHistory();
  page("chat");
}
function newConversation() {
  if (running) return toast("Detén la respuesta antes de abrir otro chat.");
  persist();
  resumeAfterLoad = false;
  current = blankSession();
  current.modelId = state.active || prefs.defaultModel || "";
  store.sessions.push(current);
  messages = current.messages;
  conversationModel = current.modelId;
  answer = "";
  chatFailure = null;
  command("clearImage");
  saveConversations();
  renderHistory();
  page("chat");
  $("prompt").value = "";
  autoSize();
}
$("newChat").onclick = newConversation;
$("drawerNewChat").onclick = newConversation;
function updateHeader() {
  const m = state.models.find((m) => m.id === (loadingModelId || state.active));
  $("activeModel").textContent =
    currentPage === "chat"
      ? m?.name || "AI Local"
      : currentPage === "library"
        ? "Modelos"
        : "GitHub";
  $("modelState").textContent =
    operationKind === "load"
      ? operationStatus || "Cargando…"
      : state.active
        ? "En tu dispositivo ⌄"
        : "Elegir modelo ⌄";
}
function beginLoad(model) {
  if (running) return toast("Hay una respuesta o carga en curso.");
  if ($("modelPicker").open) $("modelPicker").close();
  loadingModelId = model.id;
  loadRequestId = makeId();
  chatFailure = null;
  setBusy(true, "load");
  toast("Cargando " + model.name + "…");
  updateHeader();
  command("load", {
    id: model.id,
    context: contextFor(model),
    requestId: loadRequestId,
    sessionId: current.id,
  });
  page("chat");
}
function loadDefault() {
  const model = [current.modelId, prefs.defaultModel]
    .map((id) =>
      state.models.find((m) => m.id === id && state.installed.includes(m.id)),
    )
    .find(Boolean);
  if (model) beginLoad(model);
  else openPicker();
}
function openPicker() {
  closeDrawer();
  renderPicker();
  $("modelPicker").showModal();
}
$("modelSwitch").onclick = openPicker;
$("closePicker").onclick = () => {
  resumeAfterLoad = false;
  $("modelPicker").close();
};
$("browseModels").onclick = () => page("library");
function renderPicker() {
  const root = $("installedModels");
  root.replaceChildren();
  const installed = state.models.filter((m) => state.installed.includes(m.id));
  for (const m of installed) {
    const b = el("button", "installed-model");
    b.append(
      el("strong", "", m.name),
      el("small", "", m.quant + (state.active === m.id ? " · Cargado" : "")),
    );
    b.disabled = running;
    b.onclick = () => {
      if (state.active === m.id && state.activeContext === contextFor(m)) {
        page("chat");
        return;
      }
      beginLoad(m);
    };
    root.append(b);
  }
  if (!installed.length)
    root.append(
      el(
        "p",
        "muted",
        "Descarga un modelo para empezar a conversar en tu teléfono.",
      ),
    );
}
function renderDefaultOptions() {
  const select = $("defaultModel");
  const signature = state.installed.join("|");
  if (select.dataset.signature === signature) return;
  select.dataset.signature = signature;
  select.replaceChildren();
  const empty = el("option", "", "Elegir al conversar");
  empty.value = "";
  select.append(empty);
  for (const m of state.models.filter((m) => state.installed.includes(m.id))) {
    const opt = el("option", "", m.name);
    opt.value = m.id;
    select.append(opt);
  }
  select.value = prefs.defaultModel;
}
function renderChat() {
  const root = $("messages"),
    follow = root.scrollHeight - root.scrollTop - root.clientHeight < 100,
    oldTop = root.scrollTop;
  root.replaceChildren();
  root.classList.toggle(
    "empty-state",
    !messages.length && !answer && operationKind !== "chat" && !chatFailure,
  );
  if (!messages.length && !answer && operationKind !== "chat" && !chatFailure) {
    const welcome = el("div", "welcome");
    const mark = el("div", "brand-mark");
    mark.innerHTML =
      '<svg viewBox="0 0 108 108" aria-hidden="true"><path fill="currentColor" d="M54 20 82 36V69L68 77V44L54 36 40 44V77L26 69V36Z"/><path fill="currentColor" opacity=".55" d="M47 51H61V80L54 85 47 80Z"/></svg>';
    welcome.append(
      mark,
      el(
        "h1",
        "",
        prefs.name
          ? "¿En qué te ayudo, " + prefs.name + "?"
          : "¿Qué quieres crear hoy?",
      ),
      el("p", "", "Tus ideas, en tu teléfono."),
    );
    if (!state.active) {
      const pick = el("button", "welcome-pick", "Elegir modelo");
      pick.onclick = openPicker;
      welcome.append(pick);
    }
    root.append(welcome);
  } else {
    for (const m of messages) {
      if (m.role === "system") continue;
      const b = el("div", "bubble " + m.role);
      b.append(
        el("small", "", m.role === "user" ? "Tú" : "AI Local"),
        el("div", "message-text", m.content),
      );
      if (m.role === "assistant") {
        const actions = el("div", "message-actions");
        const copy = el("button", "quiet", "Copiar");
        copy.onclick = async () => {
          try {
            await navigator.clipboard.writeText(m.content);
            toast("Respuesta copiada.");
          } catch (_) {
            toast("No se pudo copiar la respuesta.", true);
          }
        };
        actions.append(copy);
        if (opened && fileSha) {
          const edit = el("button", "quiet to-github", "Llevar a GitHub ↗");
          edit.onclick = () =>
            confirmAction(
              "Copiar al editor",
              "La respuesta sustituirá el contenido del editor. Revísalo antes de guardar.",
              () => {
                const match = m.content.match(
                  /^```[^\n]*\n([\s\S]*?)\n```\s*$/,
                );
                $("editor").value = match ? match[1] : m.content;
                page("github");
              },
            );
          actions.append(edit);
        }
        b.append(actions);
      }
      root.append(b);
    }
    if (operationKind === "chat") {
      const b = el("div", "bubble assistant");
      b.append(
        el("small", "", "AI Local"),
        el("div", "message-text streaming", answer || progressText()),
      );
      root.append(b);
    }
  }
  if (operationKind === "load") {
    const status = el("div", "model-progress", progressText());
    status.setAttribute("role", "status");
    root.append(status);
  }
  if (chatFailure && !running) {
    const error = el("div", "operation-error");
    error.setAttribute("role", "alert");
    error.append(el("p", "", chatFailure.message));
    const actions = el("div", "message-actions");
    const failed = { ...chatFailure };
    if (
      failed.action === "load" ||
      messages.at(-1)?.role === "user" ||
      messages.at(-1)?.incomplete
    ) {
      const retry = el("button", "quiet retry-operation", "Reintentar");
      retry.onclick = () => {
        if (failed.action === "load") {
          const model = state.models.find((m) => m.id === failed.modelId);
          if (model) beginLoad(model);
          else openPicker();
        } else {
          if (messages.at(-1)?.incomplete) {
            messages.pop();
            persist();
          }
          if (state.active) startChat();
          else {
            resumeAfterLoad = true;
            loadDefault();
          }
        }
      };
      actions.append(retry);
    }
    const change = el("button", "quiet", "Elegir modelo");
    change.onclick = openPicker;
    actions.append(change);
    error.append(actions);
    root.append(error);
  }
  root.scrollTop = follow ? root.scrollHeight : oldTop;
}
function progressText() {
  const seconds = Math.floor((Date.now() - operationStarted) / 1000);
  return (
    (operationStatus || "Preparando…") + (seconds ? " · " + seconds + " s" : "")
  );
}
function setBusy(value, kind = null) {
  clearInterval(busyTimer);
  running = value;
  operationKind = value ? kind || operationKind : null;
  if (value) operationStopped = false;
  operationStarted = value ? Date.now() : 0;
  operationStatus = value
    ? operationKind === "load"
      ? "Abriendo modelo…"
      : "Procesando mensaje…"
    : "";
  if (value)
    busyTimer = setInterval(() => {
      if (!answer) renderChat();
    }, 1000);
  $("send").disabled = value;
  $("attach").disabled = value;
  $("newChat").disabled = value;
  $("drawerNewChat").disabled = value;
  $("deleteCurrent").disabled = value;
  $("clearHistory").disabled = value;
  $("stop").classList.toggle("hidden", !value);
  $("send").classList.toggle("hidden", value);
  renderHistory();
  updateHeader();
}
function autoSize() {
  $("prompt").style.height = "auto";
  $("prompt").style.height = Math.min(150, $("prompt").scrollHeight) + "px";
}
$("prompt").oninput = autoSize;
$("send").onclick = () => {
  const text = $("prompt").value.trim();
  if (!text || running) return;
  if (!state.active) {
    openPicker();
    return toast("Elige un modelo para enviar tu mensaje.");
  }
  const m = state.models.find((m) => m.id === state.active);
  if (attachment && !m?.vision)
    return toast("Elige un modelo de visión para interpretar imágenes.", true);
  conversationModel = state.active;
  messages.push({ role: "user", content: text });
  persist();
  $("prompt").value = "";
  autoSize();
  startChat();
};
function startChat() {
  if (running) return;
  chatFailure = null;
  current.failure = null;
  current.pending = true;
  current.requestId = makeId();
  persist();
  answer = "";
  setBusy(true, "chat");
  renderChat();
  command("chat", {
    requestId: current.requestId,
    sessionId: current.id,
    maxTokens: Number($("responseTokens").value) || 512,
    messages: [
      {
        role: "system",
        content: prefs.instructions || defaultPrefs.instructions,
      },
      ...messages,
    ],
  });
}
$("stop").onclick = () => {
  operationStopped = true;
  operationStatus = "Deteniendo…";
  updateHeader();
  renderChat();
  command("stop");
  toast("Deteniendo…");
};
$("attach").onclick = () => {
  const m = state.models.find((m) => m.id === state.active);
  if (!m?.vision)
    return toast("Carga un modelo de visión para adjuntar imágenes.", true);
  command("image");
};
$("removeImage").onclick = () => command("clearImage");

function contextFor(model) {
  return Math.max(
    model.vision ? 2048 : 512,
    Number($("contextTokens").value) || 1024,
  );
}
function memoryEstimate(model, context = contextFor(model)) {
  const weights =
    model.files.reduce((sum, file) => sum + file.size, 0) / 1073741824;
  const elements = model.kvElementsPerToken * context;
  // K=Q8_0 (34 bytes/32 elements), V=F16; include F16 fallback in the upper bound.
  const lower =
    weights +
    (elements * 1.53125) / 1073741824 +
    (model.vision ? 0.375 : 0.125);
  const upper =
    weights + (elements * 2) / 1073741824 + (model.vision ? 0.75 : 0.375);
  return { lower, upper, context, weights };
}
function assessModel(model, device = state) {
  const estimate = memoryEstimate(model),
    reasons = [];
  const installed = (device.installed || []).includes(model.id);
  const bytes = model.files.reduce((sum, file) => sum + file.size, 0);
  let level = "fit",
    label = "Margen estimado suficiente";
  if (
    !installed &&
    (!Number.isFinite(device.storage) ||
      device.storage * 1073741824 < bytes + 268435456)
  ) {
    level = "storage";
    label = "Espacio insuficiente";
    reasons.push(
      "Se necesitan " +
        ((bytes + 268435456) / 1073741824).toFixed(1) +
        " GiB libres para descargar.",
    );
  } else if (
    !Number.isFinite(device.available) ||
    !Number.isFinite(device.budget)
  ) {
    level = "caution";
    label = "Memoria disponible sin medir";
    reasons.push("No se pudo medir la memoria disponible.");
  } else if (estimate.lower > device.ram) {
    level = "large";
    label = "No recomendado";
    reasons.push(
      "La estimación (" +
        estimate.lower.toFixed(2) +
        "–" +
        estimate.upper.toFixed(2) +
        " GiB) supera los " +
        device.ram.toFixed(1) +
        " GiB de RAM física visible.",
    );
  } else if (
    device.lowMemory ||
    device.pressure ||
    device.budget < estimate.upper
  ) {
    level = "caution";
    label =
      device.budget >= estimate.lower
        ? "Posible con margen ajustado"
        : "Podría necesitar más RAM libre";
    reasons.push(
      "Estimación " +
        estimate.lower.toFixed(2) +
        "–" +
        estimate.upper.toFixed(2) +
        " GiB; disponible ahora " +
        device.available.toFixed(1) +
        " GiB.",
    );
    if (device.budget < estimate.lower)
      reasons.push("Cierra otras apps para liberar memoria antes de probar.");
    if (device.lowMemory || device.pressure)
      reasons.push("Android indica memoria baja o presión de memoria.");
  }
  return {
    recommended: level === "fit",
    level,
    label,
    reasons,
    bytes,
    estimate,
  };
}
$("contextTokens").onchange = () => {
  prefs.context = Number($("contextTokens").value);
  savePrefs();
  renderModels();
  renderPicker();
};
function visibleModels() {
  const query = $("modelSearch").value.trim().toLocaleLowerCase("es");
  return state.models.filter(
    (m) =>
      (filter === "all" ||
        (filter === "powerful" && m.parameters >= 5) ||
        filter === m.kind ||
        (filter === "installed" && state.installed.includes(m.id))) &&
      (!query ||
        (m.name + " " + m.repo + " " + m.description)
          .toLocaleLowerCase("es")
          .includes(query)),
  );
}
$("modelSearch").oninput = () => renderModels();
function el(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined) e.textContent = text;
  return e;
}
function toast(text, error = false) {
  $("toast").textContent = text || "Ocurrió un error";
  $("toast").className = error ? "error" : "";
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => ($("toast").className = "hidden"), 7500);
}
function confirmAction(title, text, fn, label = "Continuar") {
  $("confirmYes").textContent = label;
  $("confirmTitle").textContent = title;
  $("confirmText").textContent = text;
  pending = fn;
  $("confirm").showModal();
}
$("confirmNo").onclick = () => {
  $("confirm").close();
  pending = null;
};
$("confirmYes").onclick = () => {
  $("confirm").close();
  if (pending) pending();
  pending = null;
};

function renderModels() {
  const root = $("models");
  root.replaceChildren();
  const visible = visibleModels();
  $("catalogCount").textContent =
    state.models.length +
    " modelos · " +
    state.models.filter((m) => m.parameters >= 5).length +
    " de 5B+";
  $("resultCount").textContent = visible.length + " modelos en esta vista";
  visible.forEach((m) => {
    const assessment = assessModel(m),
      available = state.installed.includes(m.id);
    const card = el("article", "card" + (m.vision ? " visual" : ""));
    card.dataset.model = m.id;
    const top = el("div", "modeltop"),
      icon = el(
        "div",
        "modelicon",
        m.vision ? "◉" : m.kind === "reasoning" ? "◇" : "⌘",
      ),
      title = el("div");
    const category = {
      vision: "IMAGEN + TEXTO",
      code: "CÓDIGO",
      reasoning: "RAZONAMIENTO",
      chat: "CONVERSACIÓN",
    }[m.kind];
    title.append(
      el("h3", "", m.name),
      el("small", "", category + " · " + m.parameters + "B · " + m.quant),
    );
    top.append(icon, title);
    card.append(top, el("p", "", m.description));
    const info = el("details", "model-details");
    info.append(el("summary", "", "Memoria y compatibilidad"));
    const stats = el("div", "stats");
    stats.append(
      el("span", "", (assessment.bytes / 1e9).toFixed(2) + " GB de descarga"),
      el("span", "", assessment.estimate.context + " tokens de contexto"),
      el(
        "span",
        "",
        assessment.estimate.lower.toFixed(2) +
          "–" +
          assessment.estimate.upper.toFixed(2) +
          " GiB estimados",
      ),
    );
    info.append(stats);
    const status = el(
      "div",
      "recommendation" + (!assessment.recommended ? " not-recommended" : ""),
    );
    status.append(el("strong", "", assessment.label));
    if (!assessment.recommended)
      status.append(el("small", "", assessment.reasons.join(" ")));
    else
      status.append(
        el(
          "small",
          "",
          "Estimación de pesos + caché KV + búferes. mmap y la memoria recuperable pueden cambiar el consumo real.",
        ),
      );
    info.append(status);
    card.append(info);
    const actions = el("div", "actions"),
      btn = el(
        "button",
        available ? "secondary" : "primary",
        available
          ? state.active === m.id && state.activeContext === contextFor(m)
            ? "En uso ✓"
            : "Cargar modelo"
          : "Descargar ↓",
      );
    btn.onclick = () => {
      if (available) {
        if (state.active === m.id && state.activeContext === contextFor(m)) {
          page("chat");
          return;
        }
        if (running) return;
        const load = () => beginLoad(m);
        // RAM estimates are advisory. Loading opens chat directly.
        if (assessModel(m).level === "large")
          confirmAction(
            "Modelo muy grande",
            assessModel(m).reasons.join("\n") +
              "\nPuedes intentar cargarlo; Android puede cerrar la app si no hay memoria suficiente.",
            load,
            "Cargar modelo",
          );
        else load();
      } else {
        const warning = assessment.recommended
          ? ""
          : assessment.label + ".\n" + assessment.reasons.join("\n") + "\n\n";
        confirmAction(
          "Descargar " + m.name,
          warning +
            (assessment.bytes / 1e9).toFixed(2) +
            " GB. Se recomienda Wi-Fi. La descarga no garantiza que el teléfono pueda ejecutar el modelo.",
          () => command("download", { id: m.id }),
        );
      }
    };
    actions.append(btn);
    card.append(actions);
    const used = (state.usage || []).find(
      (u) => u.id === m.id && u.context === contextFor(m),
    );
    if (used) {
      card.append(
        el(
          "p",
          "usage-result",
          "Último chat en este teléfono · " +
            used.context +
            " de contexto · " +
            used.tokens +
            " tokens · " +
            used.tps.toFixed(1) +
            " tokens/s · PSS máximo muestreado " +
            used.peakPssMiB.toFixed(0) +
            " MiB",
        ),
      );
    }
    const progress = el("div", "hidden");
    progress.id = "progress-" + m.id;
    card.append(progress);
    if (available) {
      const remove = el("button", "quiet", "Eliminar del teléfono");
      remove.onclick = () => {
        if (running)
          return toast("Espera a que termine la operación del modelo.");
        confirmAction(
          "Eliminar modelo",
          "Se borrarán los archivos descargados de " + m.name + ".",
          () => {
            if (running) return;
            setBusy(true, "delete");
            command("delete", { id: m.id });
          },
        );
      };
      card.append(remove);
    }
    root.append(card);
  });
  for (const data of downloads.values()) drawDownload(data);
  if (!root.children.length)
    root.append(
      el("div", "empty", "No hay modelos que coincidan con estos filtros."),
    );
}

$("connect").onclick = () => {
  const token = $("token").value;
  if (!token.trim()) return toast("Introduce un token de GitHub.", true);
  command("connect", { token });
  $("token").value = "";
};
$("disconnect").onclick = () => command("disconnect");
$("repos").onclick = () => command("repos");
$("repoSelect").onchange = () => {
  const opt = $("repoSelect").selectedOptions[0];
  $("branch").value = opt.dataset.branch || "main";
  fileSha = "";
  opened = null;
  $("editorArea").classList.add("hidden");
  $("directory").replaceChildren();
};
$("read").onclick = () => {
  fileSha = "";
  opened = {
    repo: $("repoSelect").value,
    branch: $("branch").value,
    path: $("filepath").value,
  };
  $("editorArea").classList.add("hidden");
  command("read", opened);
};
$("save").onclick = () => {
  if (!fileSha || !opened)
    return toast("Abre el archivo antes de guardarlo.", true);
  if (!$("commit").value.trim())
    return toast("Escribe el mensaje del commit.", true);
  const data = {
    ...opened,
    sha: fileSha,
    text: $("editor").value,
    message: $("commit").value,
  };
  confirmAction(
    "Guardar en GitHub",
    data.repo +
      " · " +
      data.branch +
      "\n" +
      data.path +
      "\n\n" +
      data.message +
      "\n\nSe creará un commit con el contenido visible en el editor.",
    () => {
      $("save").disabled = true;
      command("write", data);
    },
  );
};

function applyInference(data) {
  if (data.instanceId) {
    if (nativeInstance === data.instanceId && data.revision < nativeRevision) {
      state.active = latestInference.active;
      state.activeContext = latestInference.activeContext;
      state.inference = latestInference;
      updateHeader();
      return;
    }
    nativeInstance = data.instanceId;
    nativeRevision = data.revision;
  }
  latestInference = data;
  state.active = data.active || "";
  state.activeContext = data.activeContext || 0;
  state.inference = data;
  $("unloadModel").disabled = !state.active || data.busy;
  $("backgroundStatus").textContent = state.active
    ? "El modelo se mantiene en segundo plano. Usa la notificación para volver o detener la respuesta."
    : "Al cargar un modelo, la app lo mantiene con una notificación y continúa las respuestas al cambiar de aplicación.";
  const job = data.job || {},
    rejected = data.rejection || {};
  if (
    rejected.id &&
    rejected.id === current.requestId &&
    !handledNativeJobs.has(rejected.id)
  ) {
    handledNativeJobs.add(rejected.id);
    receive("operationError", {
      action: rejected.action,
      message: rejected.message,
    });
    receive("done", false);
  }
  if (recoveringPending) {
    recoveringPending = false;
    if (job.id !== current.requestId || !job.sessionId) {
      current.pending = false;
      chatFailure = current.failure = {
        action: "chat",
        message:
          "La respuesta anterior se interrumpió. Puedes reintentar tu mensaje.",
      };
      persist();
      setBusy(false);
    }
  }
  const target = store.sessions.find((s) => s.id === job.sessionId);
  const conflicting =
    target?.pending && target.requestId && target.requestId !== job.id;
  if (job.id && !conflicting) {
    if (
      job.status === "running" &&
      !handledNativeJobs.has(job.id) &&
      target?.appliedRequestId !== job.id
    ) {
      if (job.action === "chat" && target) {
        if (current !== target) {
          current = target;
          messages = current.messages;
          conversationModel = current.modelId || state.active;
        }
        current.pending = true;
        current.requestId = job.id;
        chatFailure = current.failure = null;
        answer = job.answer || "";
      }
      if (job.action === "load") loadingModelId = job.modelId;
      if (!running || operationKind !== job.action) setBusy(true, job.action);
      operationStarted = job.startedAt || Date.now();
      if (job.progress)
        receive("progress", { ...job.progress, action: job.action });
      renderChat();
    } else if (!handledNativeJobs.has(job.id)) {
      handledNativeJobs.add(job.id);
      if (
        job.action === "chat" &&
        target &&
        target.appliedRequestId !== job.id
      ) {
        target.requestId = job.id;
        target.appliedRequestId = job.id;
        const failure = job.error
          ? { action: "chat", message: job.error, modelId: job.modelId }
          : null;
        if (current === target) {
          if (!running || operationKind !== "chat") setBusy(true, "chat");
          answer = job.answer || "";
          chatFailure = failure;
          if (job.metrics) receive("metrics", job.metrics);
          receive("done", job.status === "success");
          if (
            job.status !== "success" &&
            messages.at(-1)?.role === "assistant"
          ) {
            messages.at(-1).incomplete = true;
            persist();
            renderChat();
          }
        } else {
          if (job.answer?.trim())
            target.messages.push({
              role: "assistant",
              content: job.answer,
              incomplete: job.status !== "success",
            });
          target.pending = false;
          target.failure = failure;
          target.updatedAt = Date.now();
          saveConversations();
          renderHistory();
        }
      } else if (job.action === "load") {
        if (
          job.status === "success" &&
          state.active &&
          (operationKind === "load" || loadRequestId === job.id)
        )
          receive("loaded", state.active);
        else if (
          job.status !== "success" &&
          (operationKind === "load" || loadRequestId === job.id)
        ) {
          receive("operationError", {
            action: "load",
            message: job.error || "La carga se interrumpió.",
          });
          receive("done", false);
        }
      } else if (job.action === "delete" && operationKind === "delete") {
        if (job.error) toast(job.error, true);
        setBusy(false);
      }
    }
  }
  if (data.releasing) {
    if (!running) setBusy(true, "unload");
  } else if (!data.busy && operationKind === "unload") setBusy(false);
  updateHeader();
  renderPicker();
  renderChat();
}
$("unloadModel").onclick = () => {
  if (running || !state.active) return;
  setBusy(true, "unload");
  command("unload");
};

window.receive = (type, data) => {
  switch (type) {
    case "state": {
      const was = state.connected;
      state = data;
      renderResources(data);
      $("repoArea").classList.toggle("hidden", !data.connected);
      $("connection").textContent = data.connected
        ? "Cuenta conectada · token cifrado en este teléfono"
        : "El token se cifra con Android Keystore. Nunca se envía al modelo.";
      if (data.connected && !was) command("repos");
      if (!data.connected) {
        $("editorArea").classList.add("hidden");
        $("repoSelect").replaceChildren();
        $("directory").replaceChildren();
        $("editor").value = "";
        fileSha = "";
        opened = null;
      }
      for (const id of state.installed) downloads.delete(id);
      renderModels();
      renderPicker();
      renderDefaultOptions();
      updateHeader();
      if (data.inference) applyInference(data.inference);
      if (typeof data.systemDark === "boolean") {
        nativeSystemDark = data.systemDark;
        if (prefs.mode === "system") applyTheme();
      }
      if (!autoLoadAttempted) {
        autoLoadAttempted = true;
        if (prefs.autoLoad && prefs.defaultModel && !state.active && !running)
          loadDefault();
      }
      break;
    }
    case "inference":
      applyInference(data);
      break;
    case "resources":
      state = { ...state, ...data };
      renderResources(state);
      renderModels();
      break;
    case "notice":
      toast(data);
      break;
    case "error":
      toast(data, true);
      $("save").disabled = false;
      break;
    case "operationError":
      if (data.action === "delete") {
        toast(data.message, true);
        break;
      }
      chatFailure = {
        action: data.action,
        message: data.message,
        modelId: loadingModelId || state.active,
      };
      break;
    case "progress": {
      if (!running || data.action !== operationKind || operationStopped) break;
      const labels = {
        weights:
          "Cargando modelo " + Math.max(0, Math.min(100, data.current)) + "%",
        context: "Preparando contexto…",
        vision: "Cargando visión…",
        image: "Procesando imagen…",
        prompt:
          "Procesando mensaje · " + data.current + "/" + data.total + " tokens",
        generate: "Generando respuesta…",
      };
      operationStatus = labels[data.phase] || "Preparando…";
      updateHeader();
      if (!answer) renderChat();
      break;
    }
    case "metrics":
      operationStopped = !!data.stopped;
      if (prefs.showStats) {
        $("chatHint").classList.remove("hidden");
        $("chatHint").textContent =
          data.context + " contexto · " + data.tps.toFixed(1) + " tokens/s";
      }
      break;
    case "loaded":
      conversationModel = data;
      if (!prefs.defaultModel) {
        prefs.defaultModel = data;
        savePrefs();
      }
      loadingModelId = "";
      chatFailure = null;
      current.failure = null;
      persist();
      setBusy(false);
      renderPicker();
      renderDefaultOptions();
      page("chat");
      toast("Modelo listo.");
      if (resumeAfterLoad && messages.at(-1)?.role === "user") {
        resumeAfterLoad = false;
        startChat();
      }
      break;
    case "answer":
      if (operationKind !== "chat") break;
      answer = data;
      renderChat();
      break;
    case "done":
      if (!running) break;
      if (operationKind === "chat") {
        if (answer.trim()) {
          messages.push({ role: "assistant", content: answer });
        } else if (!chatFailure) {
          chatFailure = {
            action: "chat",
            message: operationStopped
              ? "Respuesta detenida. Puedes reintentar el mensaje."
              : "El modelo no devolvió texto. Reintenta el mensaje o vuelve a cargar el modelo.",
          };
        }
        current.pending = false;
        current.failure = chatFailure;
        persist();
        answer = "";
        if (data !== false) {
          attachment = false;
          $("attachment").classList.add("hidden");
        }
      } else if (data === false && !chatFailure) {
        chatFailure = {
          action: "load",
          modelId: loadingModelId,
          message: "No se pudo cargar el modelo. Puedes reintentar la carga.",
        };
      }
      loadingModelId = "";
      setBusy(false);
      renderChat();
      break;
    case "idle":
      if (running && !["delete", "unload"].includes(operationKind)) break;
      loadingModelId = "";
      setBusy(false);
      break;
    case "image":
      attachment = data;
      $("attachment").classList.toggle("hidden", !data);
      break;
    case "download":
      if (data.status === 16) downloads.delete(data.id);
      else downloads.set(data.id, data);
      drawDownload(data);
      break;
    case "repos": {
      const select = $("repoSelect"),
        old = select.value;
      select.replaceChildren(el("option", "", "Selecciona un repositorio"));
      select.firstChild.value = "";
      for (const r of data) {
        const opt = el("option", "", r.full_name);
        opt.value = r.full_name;
        opt.dataset.branch = r.default_branch;
        select.append(opt);
      }
      select.value = old;
      break;
    }
    case "file":
      opened = { repo: data.repo, branch: data.branch, path: data.path };
      $("repoSelect").value = data.repo;
      $("branch").value = data.branch;
      $("filepath").value = data.path;
      data = data.result;
      if (Array.isArray(data)) {
        const root = $("directory");
        root.replaceChildren();
        for (const f of data) {
          const b = el("button", "", (f.type === "dir" ? "▦ " : "↳ ") + f.name);
          b.onclick = () => {
            $("filepath").value = f.path;
            $("read").click();
          };
          root.append(b);
        }
      } else {
        fileSha = data.sha;
        $("editor").value = data.text;
        $("editorArea").classList.remove("hidden");
        $("directory").replaceChildren();
      }
      break;
    case "saved":
      if (
        opened &&
        opened.repo === data.repo &&
        opened.path === data.path &&
        opened.branch === data.branch
      )
        fileSha = data.sha;
      $("save").disabled = false;
      toast("Commit guardado en GitHub.");
      break;
    case "systemTheme":
      nativeSystemDark = data;
      if (prefs.mode === "system") applyTheme();
      break;
  }
};
function drawDownload(data) {
  const p = $("progress-" + data.id);
  if (!p) return;
  p.className = data.status === 16 ? "hidden" : "";
  p.replaceChildren();
  if (data.status === 16) return;
  const progress = el("progress");
  progress.max = data.total;
  progress.value = data.bytes;
  p.append(
    el(
      "small",
      "",
      data.status === 8
        ? "Verificando archivo…"
        : Math.min(100, (100 * data.bytes) / data.total).toFixed(0) +
            "% · " +
            data.file,
    ),
    progress,
  );
  const cancel = el("button", "quiet", "Cancelar descarga");
  cancel.onclick = () => {
    downloads.delete(data.id);
    command("cancel", { id: data.id });
    renderModels();
  };
  p.append(cancel);
}

$("askFile").onclick = () => {
  if (!state.active) return toast("Carga primero un modelo de código.", true);
  if (!opened) return;
  const text = $("editor").value;
  if (text.length > 10000)
    return toast(
      "El archivo es largo. Copia solo el fragmento que necesitas al chat.",
      true,
    );
  $("prompt").value =
    "Revisa este archivo y explica las mejoras que propones.\n" +
    opened.repo +
    "/" +
    opened.path +
    "\n\n" +
    text;
  page("chat");
  toast("Archivo preparado en el chat. Añade tu petición y pulsa Enviar.");
};

function renderResources(data) {
  $("deviceTitle").textContent = data.device || "Tu dispositivo";
  $("deviceDetail").textContent =
    "Disponible ahora: " +
    data.available.toFixed(1) +
    " GiB · " +
    data.storage.toFixed(1) +
    " GB de espacio";
  $("ramTotal").textContent = data.ram.toFixed(1) + " GiB";
  $("ramFree").textContent = data.available.toFixed(1) + " GiB";
  $("ramBudget").textContent = data.budget.toFixed(1) + " GiB";
  $("ramReserve").textContent = data.reserve.toFixed(1) + " GiB";
  $("resourceSource").textContent =
    (data.source || "Medición del sistema") +
    " · " +
    (data.lowMemory
      ? "Memoria baja"
      : data.pressure
        ? "Presión de memoria"
        : data.pressureKnown === false
          ? "Presión de memoria no accesible"
          : "Sin presión detectada") +
    (data.pssMiB !== undefined
      ? " · App PSS " + data.pssMiB.toFixed(0) + " MiB"
      : "") +
    ". El margen orientativo no es un límite impuesto por Android ni bloquea la carga de un 7B por una estimación.";
}
$("refreshResources").onclick = () => {
  command("state");
  toast("Actualizando recursos del teléfono…");
};

function rgb(hex) {
  return [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16));
}
function luminance(c) {
  return c
    .map((v) => {
      v /= 255;
      return v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
    })
    .reduce((sum, v, i) => sum + v * [0.2126, 0.7152, 0.0722][i], 0);
}
function contrast(a, b) {
  const x = luminance(a),
    y = luminance(b);
  return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05);
}
function applyTheme() {
  const light =
    prefs.mode === "light" ||
    (prefs.mode === "system" &&
      !(
        nativeSystemDark ??
        window.matchMedia("(prefers-color-scheme: dark)").matches
      ));
  document.documentElement.dataset.mode = light ? "light" : "dark";
  const c = rgb(prefs.accent),
    background = rgb(light ? "#ebe6dd" : "#2b2926");
  let text = c.slice();
  const target = light ? [0, 0, 0] : [255, 255, 255];
  for (let i = 0; i < 16 && contrast(text, background) < 4.5; i++)
    text = text.map((v, j) => Math.round(v * 0.85 + target[j] * 0.15));
  const style = document.documentElement.style;
  style.setProperty("--accent", prefs.accent);
  style.setProperty("--accent-text", "rgb(" + text.join(",") + ")");
  style.setProperty("--accent-soft", "rgba(" + c.join(",") + ",.12)");
  style.setProperty(
    "--accent-ink",
    contrast(c, [0, 0, 0]) >= contrast(c, [255, 255, 255])
      ? "#171514"
      : "#ffffff",
  );
  $("customAccent").value = prefs.accent;
  document
    .querySelectorAll("[data-accent]")
    .forEach((b) =>
      b.setAttribute(
        "aria-pressed",
        String(b.dataset.accent.toLowerCase() === prefs.accent.toLowerCase()),
      ),
    );
  command("appearance", { light });
}
function updateProfile() {
  const name = prefs.name.trim();
  $("profileName").textContent = name || "Mi perfil";
  $("avatar").textContent = [...(name || "T")][0].toLocaleUpperCase("es");
}
function openSettings() {
  closeDrawer();
  $("displayName").value = prefs.name;
  $("themeMode").value = prefs.mode;
  $("autoLoad").checked = !!prefs.autoLoad;
  $("showStats").checked = !!prefs.showStats;
  $("instructions").value = prefs.instructions;
  renderDefaultOptions();
  $("defaultModel").value = prefs.defaultModel;
  $("settings").showModal();
}
$("profileButton").onclick = openSettings;
$("closeSettings").onclick = () => $("settings").close();
$("settings").addEventListener("close", () => $("menuToggle").focus());
$("modelPicker").addEventListener("close", () => $("modelSwitch").focus());
$("displayName").oninput = () => {
  prefs.name = $("displayName").value.trim().slice(0, 40);
  savePrefs();
  updateProfile();
  if (!messages.length) renderChat();
};
$("themeMode").onchange = () => {
  prefs.mode = $("themeMode").value;
  savePrefs();
  applyTheme();
};
document.querySelectorAll("[data-accent]").forEach(
  (b) =>
    (b.onclick = () => {
      prefs.accent = b.dataset.accent;
      savePrefs();
      applyTheme();
    }),
);
$("customAccent").oninput = () => {
  const color = $("customAccent").value;
  if (/^#[0-9a-f]{6}$/i.test(color)) {
    prefs.accent = color;
    savePrefs();
    applyTheme();
  }
};
$("defaultModel").onchange = () => {
  prefs.defaultModel = $("defaultModel").value;
  savePrefs();
};
$("autoLoad").onchange = () => {
  prefs.autoLoad = $("autoLoad").checked;
  savePrefs();
};
$("responseTokens").onchange = () => {
  prefs.response = Number($("responseTokens").value);
  savePrefs();
};
$("instructions").oninput = () => {
  prefs.instructions = $("instructions").value.slice(0, 4000);
  savePrefs();
};
$("showStats").onchange = () => {
  prefs.showStats = $("showStats").checked;
  savePrefs();
  if (!prefs.showStats) {
    $("chatHint").textContent = "";
    $("chatHint").classList.add("hidden");
  }
};
$("deleteCurrent").onclick = () => {
  if (running) return;
  confirmAction(
    "Eliminar conversación",
    "Se eliminará «" + current.title + "» de este teléfono.",
    () => {
      store.sessions = store.sessions.filter((s) => s.id !== current.id);
      if (!store.sessions.length) store.sessions.push(blankSession());
      current = store.sessions[0];
      messages = current.messages;
      conversationModel = current.modelId || "";
      answer = "";
      chatFailure = current.failure || null;
      saveConversations();
      renderHistory();
      page("chat");
    },
  );
};
$("clearHistory").onclick = () => {
  if (running) return;
  confirmAction(
    "Eliminar todo el historial",
    "Se borrarán las conversaciones de este teléfono. Tus modelos y la conexión con GitHub se conservarán.",
    () => {
      current = blankSession();
      store.sessions = [current];
      messages = current.messages;
      conversationModel = "";
      answer = "";
      chatFailure = null;
      saveConversations();
      renderHistory();
      page("chat");
    },
  );
};
document.querySelectorAll("[data-filter]").forEach(
  (b) =>
    (b.onclick = () => {
      filter = b.dataset.filter;
      document
        .querySelectorAll("[data-filter]")
        .forEach((x) => x.classList.toggle("selected", x === b));
      renderModels();
    }),
);
window
  .matchMedia("(prefers-color-scheme: dark)")
  .addEventListener("change", () => {
    if (prefs.mode === "system" && nativeSystemDark === null) applyTheme();
  });
applyTheme();
updateProfile();
renderHistory();
renderChat();
if (recoveringPending) {
  setBusy(true, "chat");
  operationStatus = "Recuperando respuesta…";
  renderChat();
}
renderModels();
renderPicker();
page("chat");
saveConversations();
