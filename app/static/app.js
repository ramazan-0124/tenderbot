const form = document.querySelector("#searchForm");
const queryInput = document.querySelector("#queryInput");
const amountInput = document.querySelector("#amountInput");
const limitInput = document.querySelector("#limitInput");
const results = document.querySelector("#results");
const phraseBox = document.querySelector("#phraseBox");
const resultCount = document.querySelector("#resultCount");
const termsLabel = document.querySelector("#termsLabel");

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  await search();
});

queryInput.value = localStorage.getItem("lastQuery") || "сервер";
amountInput.value = localStorage.getItem("lastAmount") || "1000000";

search();

async function search() {
  const query = queryInput.value.trim();
  const minAmount = amountInput.value || "0";
  const limit = limitInput.value || "30";
  if (!query) return;

  localStorage.setItem("lastQuery", query);
  localStorage.setItem("lastAmount", minAmount);

  setLoading(true);
  try {
    const url = `/api/search?q=${encodeURIComponent(query)}&min_amount=${encodeURIComponent(minAmount)}&limit=${encodeURIComponent(limit)}`;
    const response = await fetch(url);
    const data = await response.json();
    render(data);
  } catch (error) {
    results.innerHTML = `<div class="empty">Ошибка поиска: ${escapeHtml(error.message)}</div>`;
  } finally {
    setLoading(false);
  }
}

function render(data) {
  resultCount.textContent = data.count || 0;
  termsLabel.textContent = (data.terms || []).slice(0, 8).join(", ") || "—";
  phraseBox.innerHTML = (data.searchPhrases || [])
    .map((phrase) => `<span class="pill">${escapeHtml(phrase)}</span>`)
    .join("");

  const items = data.items || [];
  if (!items.length) {
    results.innerHTML = `<div class="empty">Ничего не найдено. Попробуй более простой запрос: “сервер”, “лицензия”, “ноутбук”.</div>`;
    return;
  }

  results.innerHTML = items.map(renderCard).join("");
}

function renderCard(item) {
  const terms = (item.matched_terms || [])
    .map((term) => `<span class="pill">${escapeHtml(term)}</span>`)
    .join("");

  return `
    <article class="card">
      <div class="card-head">
        <div>
          <h2 class="title">${escapeHtml(item.title || item.announcement)}</h2>
          <p class="lot-number">${escapeHtml(item.lot_number)} · ${escapeHtml(item.announcement)}</p>
        </div>
        <div class="score">${item.score}</div>
      </div>

      <div class="meta">
        <div class="meta-item"><b>Сумма</b><span>${formatAmount(item.amount)} тг</span></div>
        <div class="meta-item"><b>Статус</b><span>${escapeHtml(item.status)}</span></div>
        <div class="meta-item"><b>Способ</b><span>${escapeHtml(item.method)}</span></div>
        <div class="meta-item"><b>Заказчик</b><span>${escapeHtml(item.customer)}</span></div>
      </div>

      <div class="matches">${terms || '<span class="muted">Совпадения не выделены</span>'}</div>
      <a class="source-link" href="${escapeAttribute(item.url)}" target="_blank" rel="noreferrer">Открыть на goszakup.gov.kz</a>
    </article>
  `;
}

function setLoading(isLoading) {
  form.querySelector("button").disabled = isLoading;
  form.querySelector("button").textContent = isLoading ? "Ищу..." : "Искать";
}

function formatAmount(value) {
  if (value === null || value === undefined) return "не указана";
  return Number(value).toLocaleString("ru-RU", {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  }).replace(/,/g, " ");
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function escapeAttribute(value) {
  return escapeHtml(value);
}
