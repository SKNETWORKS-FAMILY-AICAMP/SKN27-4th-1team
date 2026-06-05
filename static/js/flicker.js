(function () {
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    return;
  }

  const minDelay = 4200;
  const maxDelay = 12000;

  function scheduleFlicker() {
    const delay = minDelay + Math.random() * (maxDelay - minDelay);

    window.setTimeout(() => {
      document.body.classList.add("page-flicker");

      window.setTimeout(() => {
        document.body.classList.remove("page-flicker");
        scheduleFlicker();
      }, 180);
    }, delay);
  }

  scheduleFlicker();
})();
