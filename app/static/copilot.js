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

  const escape = (text) => String(text ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
  const paragraphs = (text) => escape(text).split(/\n\n+/).map((p) => `<p>${p}</p>`).join("");
  const sourceList = (sources) => {
    const items = (sources || []).map((s, i) => `<li>[${i + 1}] <strong>${escape(s.section)}</strong> · ${escape(s.title)}</li>`).join("");
    return items ? `<ol class="answer-sources">${items}</ol>` : "";
  };

  // What produced the answer, in a few words.
  const modeTag = (data) => ({
    llm: `<p class="ai-tag">AI draft · ${escape(data.endpoint || "model endpoint")} · checked against the sources</p>`,
    template: '<p class="ai-tag ai-tag-offline">Template draft · no model connected</p>',
    briefing: '<p class="ai-tag">Summary of this decision</p>',
    route: '<p class="route-tag">Numbers question → Genie</p>',
    offline: '<p class="ai-tag ai-tag-offline">From the supplier documents</p>',
  })[data.mode] || "";

  // Thumbs up or down, so bad answers become evaluation questions.
  const feedback = (kind, item, question, data) => {
    if (data.mode === "route" || !(data.sources || []).length) return "";
    const wrap = document.createElement("div");
    wrap.className = "feedback";
    wrap.innerHTML = 'Useful? <button type="button" data-vote="up" aria-pressed="false">👍</button><button type="button" data-vote="down" aria-pressed="false">👎</button>';
    wrap.querySelectorAll("button").forEach((button) => {
      button.addEventListener("click", async () => {
        wrap.querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", String(b === button)));
        try {
          await fetch("/api/feedback", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ kind, item, question, vote: button.dataset.vote, mode: data.mode,
                                   sources: (data.sources || []).map((s) => s.section) }),
          });
        } catch (error) { /* feedback is best effort */ }
      });
    });
    return wrap;
  };

  const render = (out, kind, item, question, data, genie) => {
    const genieLink = data.mode === "route" && genie
      ? `<a class="button button-small button-secondary" href="${escape(genie)}" target="_blank" rel="noopener">Open in Genie ↗</a>` : "";
    const to = kind === "briefing" && out.dataset.to ? `<p class="draft-to">To: ${escape(out.dataset.to)}</p>` : "";
    const sources = kind === "briefing" ? "" : sourceList(data.sources);  // the page lists the briefing's sources
    out.innerHTML = `${modeTag(data)}${to}${paragraphs(data.answer)}${genieLink}${sources}`;
    const votes = feedback(kind, item, question, data);
    if (!votes) return;
    if (kind === "briefing" && navigator.clipboard) {
      const copy = document.createElement("button");
      copy.type = "button";
      copy.className = "text-button";
      copy.textContent = "Copy";
      copy.addEventListener("click", async () => {
        await navigator.clipboard.writeText(data.answer);
        copy.textContent = "Copied";
      });
      votes.prepend(copy);
    }
    out.appendChild(votes);
  };

  const post = async (url, payload) => {
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Request failed");
    return data;
  };

  const bindAsk = () => {
    const form = document.querySelector("#ask-form");
    if (!form) return;
    const input = form.querySelector("#ask-input");
    const answer = form.querySelector("#ask-answer");

    const submit = async (question) => {
      if (!question.trim()) return;
      answer.hidden = false;
      answer.innerHTML = '<p class="muted">Searching supplier documents…</p>';
      try {
        const data = await post("/api/ask", { question, item: form.dataset.item, approved: form.dataset.approved || "" });
        render(answer, "ask", form.dataset.item, question, data, form.dataset.genie);
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

  const bindBriefing = () => {
    const box = document.querySelector("#ai-briefing");
    if (!box) return;
    const button = box.querySelector("#ai-briefing-button");
    const out = box.querySelector("#ai-briefing-answer");

    button.addEventListener("click", async () => {
      button.disabled = true;
      out.hidden = false;
      out.innerHTML = '<p class="muted">Drafting…</p>';
      try {
        const data = await post("/api/briefing", { item: box.dataset.item, approved: box.dataset.approved || "" });
        render(out, "briefing", box.dataset.item, "", data);
      } catch (error) {
        out.innerHTML = `<p class="muted">${escape(error.message)}</p>`;
      } finally {
        button.disabled = false;
      }
    });
  };

  drawProjection();
  bindAsk();
  bindBriefing();
})();
