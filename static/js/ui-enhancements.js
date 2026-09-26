document.addEventListener("DOMContentLoaded", function () {
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const revealItems = document.querySelectorAll("[data-reveal]");

  if (reducedMotion || !("IntersectionObserver" in window)) {
    revealItems.forEach((item) => item.classList.add("is-visible"));
  } else {
    const observer = new IntersectionObserver((entries, currentObserver) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add("is-visible");
        currentObserver.unobserve(entry.target);
      });
    }, { threshold: 0.12 });
    revealItems.forEach((item) => observer.observe(item));
  }

  document.querySelectorAll(".btn-primary, .btn-outline-primary, .quick-suggestion").forEach((button) => {
    button.classList.add("ripple-target");
    button.addEventListener("click", function (event) {
      if (reducedMotion || event.defaultPrevented) return;
      const rect = button.getBoundingClientRect();
      const ripple = document.createElement("span");
      ripple.className = "rm-ripple";
      ripple.style.left = `${event.clientX - rect.left}px`;
      ripple.style.top = `${event.clientY - rect.top}px`;
      button.querySelector(".rm-ripple")?.remove();
      button.appendChild(ripple);
    });
  });
});
