(() => {
  const ns = "http://www.w3.org/2000/svg";

  const drawProjection = () => {
    const chart = document.querySelector("#projection-chart");
    const source = document.querySelector("#projection-data");
    if (!chart || !source) return;

    const rows = JSON.parse(source.textContent);
    const width = 640;
    const height = 220;
    const pad = { top: 14, right: 10, bottom: 30, left: 40 };
    const plotW = width - pad.left - pad.right;
    const plotH = height - pad.top - pad.bottom;
    const values = rows.flatMap((r) => [r.forecast_units, r.delivery_units, r.projected_stock, 0]);
    const raw = Math.max(...values) - Math.min(...values) || 50;
    const step = [10, 20, 25, 50, 100, 200, 250, 500].find((s) => raw / s <= 5) || 1000;
    const yMax = Math.ceil(Math.max(...values) / step) * step || step;
    const yMin = Math.min(0, Math.floor(Math.min(...values) / step) * step);
    const ticks = Math.round((yMax - yMin) / step);
    const y = (v) => pad.top + ((yMax - v) / (yMax - yMin)) * plotH;
    const slot = plotW / rows.length;
    const x = (i) => pad.left + slot * i + slot / 2;

    const el = (name, attrs, text) => {
      const node = document.createElementNS(ns, name);
      for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
      if (text !== undefined) node.textContent = text;
      chart.appendChild(node);
      return node;
    };

    rows.forEach((r, i) => {
      if (r.promo) {
        el("rect", { x: pad.left + slot * i, y: pad.top, width: slot, height: plotH, class: "promo-band" });
      }
    });
    for (let t = 0; t <= ticks; t += 1) {
      const v = yMin + step * t;
      el("line", { x1: pad.left, x2: width - pad.right, y1: y(v), y2: y(v), class: v === 0 ? "zero" : "grid" });
      el("text", { x: pad.left - 8, y: y(v) + 4, class: "axis", "text-anchor": "end" }, Math.round(v));
    }
    rows.forEach((r, i) => {
      const bar = slot * 0.34;
      el("rect", { x: x(i) - bar - 1, y: y(r.forecast_units), width: bar,
                   height: Math.max(0, y(0) - y(r.forecast_units)), class: "bar-forecast", rx: 2 });
      if (r.delivery_units > 0) {
        el("rect", { x: x(i) + 1, y: y(r.delivery_units), width: bar,
                     height: Math.max(0, y(0) - y(r.delivery_units)), class: "bar-delivery", rx: 2 });
      }
      const day = new Date(`${r.date}T00:00:00`).toLocaleDateString("en-GB", { weekday: "short", day: "numeric" });
      el("text", { x: x(i), y: height - 9, class: "axis", "text-anchor": "middle" }, day);
    });
    const path = rows.map((r, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(r.projected_stock).toFixed(1)}`).join(" ");
    el("path", { d: path, class: "line-stock" });
    rows.forEach((r, i) => {
      el("circle", { cx: x(i), cy: y(r.projected_stock), r: 4, class: r.projected_stock < 0 ? "dot-out" : "dot-stock" });
    });
  };

  const bindAsk = () => {
    const form = document.querySelector("#ask-form");
    if (!form) return;
    const input = form.querySelector("#ask-input");
    const answer = form.querySelector("#ask-answer");

    const escape = (text) => text.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);

    const submit = async (question) => {
      if (!question.trim()) return;
      answer.hidden = false;
      answer.innerHTML = '<p class="muted">Searching supplier knowledge…</p>';
      try {
        const response = await fetch("/api/ask", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question, item: form.dataset.item }),
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "Request failed");
        const paragraphs = escape(data.answer).split(/\n\n+/).map((p) => `<p>${p}</p>`).join("");
        const sources = data.sources.map((s, i) => `<li>[${i + 1}] <strong>${escape(s.section)}</strong> · ${escape(s.title)}</li>`).join("");
        answer.innerHTML = `${paragraphs}${sources ? `<ol class="answer-sources">${sources}</ol>` : ""}`;
      } catch (error) {
        answer.innerHTML = `<p class="muted">${escape(error.message)}</p>`;
      }
    };

    form.addEventListener("submit", (event) => {
      event.preventDefault();
      submit(input.value);
    });
    form.querySelectorAll("[data-q]").forEach((button) => {
      button.addEventListener("click", () => {
        input.value = button.dataset.q;
        submit(button.dataset.q);
      });
    });
  };

  drawProjection();
  bindAsk();
})();
