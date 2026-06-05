(function () {
  if (window.__goeiFlickerStarted) {
    return;
  }

  window.__goeiFlickerStarted = true;

  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    return;
  }

  const minDelay = 4200;
  const maxDelay = 12000;
  const faceLayer = document.createElement("div");

  faceLayer.className = "flicker-face";
  faceLayer.setAttribute("aria-hidden", "true");
  document.body.append(faceLayer);

  function scheduleFlicker() {
    const delay = minDelay + Math.random() * (maxDelay - minDelay);

    window.setTimeout(() => {
      const randomX = 34 + Math.random() * 32;
      const randomY = 32 + Math.random() * 34;

      faceLayer.style.setProperty("--flicker-face-x", `${randomX}%`);
      faceLayer.style.setProperty("--flicker-face-y", `${randomY}%`);
      document.body.classList.add("page-flicker");

      window.setTimeout(() => {
        document.body.classList.remove("page-flicker");
        scheduleFlicker();
      }, 180);
    }, delay);
  }

  scheduleFlicker();
})();
