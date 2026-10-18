(() => {
  const chart = document.querySelector("#demand-chart");
  const source = document.querySelector("#chart-data");
  const tip = document.querySelector("#chart-tip");
  if (!chart || !source) return;

  const data = JSON.parse(source.textContent);
  const width = 1200;
  const height = 380;
  const pad = { top: 16, right: 16, bottom: 36, left: 56 };
  const plotWidth = width - pad.left - pad.right;
  const plotHeight = height - pad.top - pad.bottom;
  const series = [
    { key: "baseline", label: "Current forecast", color: "#7d909b", width: 3, dash: "3 9" },
    { key: "actual", label: "Actual", color: "#f2f5f6", width: 3.4, draw: true },
    { key: "improved", label: "Improved forecast", color: "#ff5a3d", width: 4.2, draw: true },
  ];

  const values = series.flatMap(({ key }) => data[key]);
  if (!values.length) return;

  const yMin = Math.floor(Math.min(...values) / 100) * 100;
  const yMax = Math.ceil(Math.max(...values) / 100) * 100 || yMin + 100;
  const yRange = yMax - yMin || 1;
  const last = Math.max(data.dates.length - 1, 1);
  const ns = "http://www.w3.org/2000/svg";

  const add = (name, attributes, text) => {
    const node = document.createElementNS(ns, name);
    for (const [key, value] of Object.entries(attributes)) node.setAttribute(key, value);
    if (text !== undefined) node.textContent = text;
    chart.appendChild(node);
    return node;
  };
  const x = (index) => pad.left + (index / last) * plotWidth;
  const y = (value) => pad.top + ((yMax - value) / yRange) * plotHeight;

  // Promotion days first so everything else draws on top.
  const step = plotWidth / last;
  let runStart = null;
  data.promo.forEach((flag, index) => {
    if (flag > 0 && runStart === null) runStart = index;
    if ((flag <= 0 || index === data.promo.length - 1) && runStart !== null) {
      const runEnd = flag > 0 ? index : index - 1;
      add("rect", {
        x: x(runStart) - step / 2,
        y: pad.top,
        width: (runEnd - runStart + 1) * step,
        height: plotHeight,
        fill: "rgba(255, 180, 84, 0.12)",
      });
      runStart = null;
    }
  });

  for (let tick = 0; tick <= 4; tick += 1) {
    const value = yMin + (yRange * tick) / 4;
    add("line", { x1: pad.left, x2: width - pad.right, y1: y(value), y2: y(value), stroke: "#1b2a33", "stroke-width": 1 });
    add("text", { x: pad.left - 12, y: y(value) + 4, fill: "#8fa1ab", "font-size": 13, "font-family": "IBM Plex Mono, monospace", "text-anchor": "end" }, Math.round(value).toLocaleString());
  }

  for (const { key, color, width: lineWidth, dash, draw } of series) {
    const path = add("path", {
      d: data[key].map((value, index) => `${index === 0 ? "M" : "L"}${x(index).toFixed(1)},${y(value).toFixed(1)}`).join(" "),
      fill: "none",
      stroke: color,
      "stroke-width": lineWidth,
      "stroke-linecap": "round",
      "stroke-linejoin": "round",
      ...(dash ? { "stroke-dasharray": dash } : {}),
      ...(draw ? { pathLength: 1, class: "draw" } : {}),
    });
    path.setAttribute("aria-hidden", "true");
  }

  const labelIndexes = new Set([0, Math.floor(last / 2), last]);
  for (const index of labelIndexes) {
    add("text", {
      x: x(index),
      y: height - 10,
      fill: "#8fa1ab",
      "font-size": 13,
      "font-family": "IBM Plex Mono, monospace",
      "text-anchor": index === 0 ? "start" : index === last ? "end" : "middle",
    }, data.dates[index]);
  }

  if (!tip) return;
  const guide = add("line", { y1: pad.top, y2: pad.top + plotHeight, stroke: "#8fa1ab", "stroke-width": 1, "stroke-dasharray": "4 5", visibility: "hidden" });
  const dots = series.map(({ color }) => add("circle", { r: 5, fill: color, stroke: "#0a1014", "stroke-width": 2, visibility: "hidden" }));
  const number = (value) => Math.round(value).toLocaleString();

  const show = (event) => {
    const box = chart.getBoundingClientRect();
    const scale = box.width / width;
    const pointer = (event.clientX - box.left) / scale;
    const index = Math.min(last, Math.max(0, Math.round(((pointer - pad.left) / plotWidth) * last)));

    guide.setAttribute("x1", x(index));
    guide.setAttribute("x2", x(index));
    guide.setAttribute("visibility", "visible");
    series.forEach(({ key }, i) => {
      dots[i].setAttribute("cx", x(index));
      dots[i].setAttribute("cy", y(data[key][index]));
      dots[i].setAttribute("visibility", "visible");
    });

    tip.replaceChildren();
    const title = document.createElement("strong");
    title.textContent = data.dates[index];
    tip.appendChild(title);
    for (const { key, label, color } of [series[1], series[0], series[2]]) {
      const row = document.createElement("div");
      const name = document.createElement("span");
      name.textContent = label;
      name.style.borderLeft = `3px solid ${color}`;
      name.style.paddingLeft = "8px";
      const value = document.createElement("b");
      value.textContent = number(data[key][index]);
      row.append(name, value);
      tip.appendChild(row);
    }
    if (data.promo[index] > 0) {
      const promo = document.createElement("div");
      promo.className = "tip-promo";
      promo.textContent = "Promotion day";
      tip.appendChild(promo);
    }
    tip.hidden = false;
    const tipWidth = tip.offsetWidth;
    const left = x(index) * scale + 16;
    tip.style.left = `${left + tipWidth > box.width ? x(index) * scale - tipWidth - 16 : left}px`;
  };
  const hide = () => {
    tip.hidden = true;
    guide.setAttribute("visibility", "hidden");
    dots.forEach((dot) => dot.setAttribute("visibility", "hidden"));
  };

  chart.addEventListener("pointermove", show);
  chart.addEventListener("pointerdown", show);
  chart.addEventListener("pointerleave", hide);
})();
