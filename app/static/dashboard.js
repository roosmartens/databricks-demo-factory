(() => {
  const chart = document.querySelector("#demand-chart");
  const source = document.querySelector("#chart-data");
  if (!chart || !source) return;

  const data = JSON.parse(source.textContent);
  const width = 960;
  const height = 280;
  const pad = { top: 12, right: 12, bottom: 32, left: 48 };
  const plotWidth = width - pad.left - pad.right;
  const plotHeight = height - pad.top - pad.bottom;
  const token = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  const series = [
    { key: "actual", color: token("--series-1"), width: 2.6 },
    { key: "baseline", color: token("--series-2"), width: 1.8 },
    { key: "improved", color: token("--series-3"), width: 1.8 },
  ];

  const values = series.flatMap(({ key }) => data[key]);
  if (!values.length) return;

  const min = Math.min(...values);
  const max = Math.max(...values);
  const yMin = Math.floor(min / 100) * 100;
  const yMax = Math.ceil(max / 100) * 100 || yMin + 100;
  const yRange = yMax - yMin || 1;
  const count = Math.max(data.dates.length - 1, 1);
  const ns = "http://www.w3.org/2000/svg";

  const element = (name, attributes, text) => {
    const node = document.createElementNS(ns, name);
    for (const [key, value] of Object.entries(attributes)) {
      node.setAttribute(key, value);
    }
    if (text !== undefined) node.textContent = text;
    chart.appendChild(node);
    return node;
  };
  const y = (value) => pad.top + ((yMax - value) / yRange) * plotHeight;

  for (let tick = 0; tick <= 4; tick += 1) {
    const value = yMin + (yRange * tick) / 4;
    const yPosition = y(value);
    element("line", {
      x1: pad.left,
      x2: width - pad.right,
      y1: yPosition,
      y2: yPosition,
      stroke: token("--subtle"),
      "stroke-width": "1",
    });
    element(
      "text",
      {
        x: pad.left - 9,
        y: yPosition + 4,
        fill: token("--faint"),
        "font-size": "10",
        "text-anchor": "end",
      },
      Math.round(value).toLocaleString(),
    );
  }

  for (const { key, color, width: lineWidth } of series) {
    const points = data[key].map((value, index) => {
      const xPosition = pad.left + (index / count) * plotWidth;
      return `${index === 0 ? "M" : "L"}${xPosition.toFixed(1)},${y(value).toFixed(1)}`;
    });
    element("path", {
      d: points.join(" "),
      fill: "none",
      stroke: color,
      "stroke-width": lineWidth,
      "stroke-linecap": "round",
      "stroke-linejoin": "round",
    });
  }

  const labels = [0, Math.floor((data.dates.length - 1) / 2), data.dates.length - 1];
  for (const index of new Set(labels)) {
    const xPosition = pad.left + (index / count) * plotWidth;
    element(
      "text",
      {
        x: xPosition,
        y: height - 7,
        fill: token("--faint"),
        "font-size": "10",
        "text-anchor": index === 0 ? "start" : index === data.dates.length - 1 ? "end" : "middle",
      },
      data.dates[index],
    );
  }
})();
