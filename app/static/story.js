(() => {
  "use strict";

  const STAGE_W = 1920;
  const STAGE_H = 1080;
  const STORAGE_KEY = "databricks-demo-factory-story-v2";

  class SlideDeck {
    constructor() {
      this.slides = [...document.querySelectorAll("[data-slide]")];
      this.stage = document.querySelector("#deck-stage");
      this.viewport = document.querySelector("#deck-viewport");
      this.counter = document.querySelector("[data-current]");
      this.progress = document.querySelector("[data-progress]");
      this.editable = [...document.querySelectorAll("[data-editable]")];
      this.status = document.querySelector("[data-edit-status]");
      this.index = 0;
      this.wheelLocked = false;

      document.querySelector("[data-total]").textContent = String(this.slides.length).padStart(2, "0");
      this.restoreEdits();
      this.bindScale();
      this.bindNavigation();
      this.bindEditing();
      this.show(this.fromHash());
    }

    fromHash() {
      const n = parseInt(window.location.hash.slice(1), 10);
      return Number.isInteger(n) ? Math.min(Math.max(n - 1, 0), this.slides.length - 1) : 0;
    }

    bindScale() {
      const fit = () => {
        const scale = Math.min(window.innerWidth / STAGE_W, window.innerHeight / STAGE_H);
        const x = (window.innerWidth - STAGE_W * scale) / 2;
        const y = (window.innerHeight - STAGE_H * scale) / 2;
        this.stage.style.transform = `translate(${x}px, ${y}px) scale(${scale})`;
      };
      fit();
      window.addEventListener("resize", fit);
    }

    bindNavigation() {
      const go = (delta) => this.show(this.index + delta);
      document.querySelector("[data-prev]").addEventListener("click", () => go(-1));
      document.querySelector("[data-next]").addEventListener("click", () => go(1));
      document.querySelector("[data-print]").addEventListener("click", () => window.print());

      document.addEventListener("keydown", (event) => {
        if (event.target.isContentEditable || event.metaKey || event.ctrlKey || event.altKey) return;
        const keys = {
          ArrowRight: 1, ArrowDown: 1, PageDown: 1, " ": 1,
          ArrowLeft: -1, ArrowUp: -1, PageUp: -1,
        };
        if (event.key in keys) {
          event.preventDefault();
          go(keys[event.key]);
        } else if (event.key === "Home") this.show(0);
        else if (event.key === "End") this.show(this.slides.length - 1);
        else if (event.key.toLowerCase() === "e") this.toggleEdit();
      });

      let startX = 0;
      let startY = 0;
      this.viewport.addEventListener("touchstart", (event) => {
        startX = event.touches[0].clientX;
        startY = event.touches[0].clientY;
      }, { passive: true });
      this.viewport.addEventListener("touchend", (event) => {
        const dx = event.changedTouches[0].clientX - startX;
        const dy = event.changedTouches[0].clientY - startY;
        if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy)) go(dx < 0 ? 1 : -1);
      }, { passive: true });

      this.viewport.addEventListener("wheel", (event) => {
        if (this.wheelLocked || document.body.classList.contains("edit-mode") || Math.abs(event.deltaY) < 30) return;
        this.wheelLocked = true;
        go(event.deltaY > 0 ? 1 : -1);
        setTimeout(() => { this.wheelLocked = false; }, 700);
      }, { passive: true });

      window.addEventListener("hashchange", () => this.show(this.fromHash()));
    }

    show(target) {
      this.index = Math.min(Math.max(target, 0), this.slides.length - 1);
      this.slides.forEach((slide, i) => {
        const on = i === this.index;
        slide.classList.toggle("active", on);
        slide.classList.toggle("visible", on);
        if (on) slide.removeAttribute("aria-hidden"); else slide.setAttribute("aria-hidden", "true");
      });
      this.counter.textContent = String(this.index + 1).padStart(2, "0");
      this.progress.style.width = `${((this.index + 1) / this.slides.length) * 100}%`;
      history.replaceState(null, "", `#${this.index + 1}`);
    }

    bindEditing() {
      const hotzone = document.querySelector(".edit-hotzone");
      const toggle = document.querySelector("#edit-toggle");
      hotzone.addEventListener("click", (event) => { if (event.target === hotzone) this.toggleEdit(); });
      toggle.addEventListener("click", () => this.toggleEdit());
      document.querySelector("[data-save-edits]").addEventListener("click", () => this.saveEdits(true));
      document.querySelector("[data-export-html]").addEventListener("click", () => this.exportHtml());
      document.querySelector("[data-reset-edits]").addEventListener("click", () => this.resetEdits());
      document.addEventListener("keydown", (event) => {
        if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "s" && document.body.classList.contains("edit-mode")) {
          event.preventDefault();
          this.saveEdits(true);
        }
      });
      this.editable.forEach((el) => el.addEventListener("input", () => this.saveEdits(false)));
    }

    toggleEdit() {
      const on = document.body.classList.toggle("edit-mode");
      this.editable.forEach((el) => {
        if (on) el.setAttribute("contenteditable", "true"); else el.removeAttribute("contenteditable");
      });
      this.setStatus(on ? "EDIT MODE · CLICK ANY TEXT" : "");
      if (!on) this.saveEdits(false);
    }

    saveEdits(announce) {
      try {
        const saved = {};
        this.editable.forEach((el, i) => { saved[i] = el.innerHTML; });
        localStorage.setItem(STORAGE_KEY, JSON.stringify(saved));
        this.setStatus(announce ? "SAVED IN THIS BROWSER" : "AUTOSAVED");
      } catch {
        this.setStatus("SAVE FAILED · CHECK BROWSER STORAGE");
      }
    }

    restoreEdits() {
      try {
        const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
        this.editable.forEach((el, i) => { if (saved[i] !== undefined) el.innerHTML = saved[i]; });
      } catch {
        localStorage.removeItem(STORAGE_KEY);
      }
    }

    resetEdits() {
      try { localStorage.removeItem(STORAGE_KEY); } catch { /* storage unavailable */ }
      window.location.hash = "";
      window.location.reload();
    }

    async exportHtml() {
      try {
        const doc = document.documentElement.cloneNode(true);
        const cssLink = doc.querySelector('link[href*="story.css"]');
        const jsTag = doc.querySelector('script[src*="story.js"]');
        const [css, js] = await Promise.all([
          fetch(cssLink.href).then((r) => r.text()),
          fetch(jsTag.src).then((r) => r.text()),
        ]);
        const style = document.createElement("style");
        style.textContent = css;
        cssLink.replaceWith(style);
        const script = document.createElement("script");
        script.textContent = js;
        jsTag.replaceWith(script);

        doc.querySelector("body").classList.remove("edit-mode");
        doc.querySelectorAll("[contenteditable]").forEach((el) => el.removeAttribute("contenteditable"));
        doc.querySelectorAll(".deck-stage").forEach((el) => el.removeAttribute("style"));
        doc.querySelectorAll("a[href]").forEach((a) => {
          if (a.getAttribute("href").startsWith("/")) a.setAttribute("href", "#");
        });

        const blob = new Blob(["<!doctype html>\n" + doc.outerHTML], { type: "text/html" });
        const link = document.createElement("a");
        link.href = URL.createObjectURL(blob);
        link.download = "demand-planning-story.html";
        link.click();
        URL.revokeObjectURL(link.href);
        this.setStatus("HTML DOWNLOAD STARTED");
      } catch {
        this.setStatus("EXPORT FAILED");
      }
    }

    setStatus(message) {
      if (this.status) this.status.textContent = message;
    }
  }

  window.addEventListener("DOMContentLoaded", () => new SlideDeck());
})();
