document.addEventListener('DOMContentLoaded', function () {
  const html = document.documentElement;
  const navbar = document.querySelector('.site-navbar');
  const toggle = document.getElementById('themeToggle');
  const storedTheme = localStorage.getItem('retiya-theme');
  const cursorDot = document.querySelector('.cursor-dot');
  const cursorRing = document.querySelector('.cursor-ring');

  if (storedTheme === 'dark') {
    html.setAttribute('data-theme', 'dark');
  }

  const applyIcon = () => {
    if (!toggle) return;
    const isDark = html.getAttribute('data-theme') === 'dark';
    toggle.innerHTML = isDark ? '<i class="bi bi-sun"></i>' : '<i class="bi bi-moon-stars"></i>';
  };

  const setupCursor = () => {
    if (!cursorDot || !cursorRing || window.matchMedia('(pointer: coarse)').matches) {
      return;
    }

    let mouseX = 0;
    let mouseY = 0;
    let ringX = 0;
    let ringY = 0;

    const hoverTargets = document.querySelectorAll('a, button, .btn, .nav-link, .card, .product-card, .social-icons a, input, select, textarea');

    window.addEventListener('pointermove', (event) => {
      mouseX = event.clientX;
      mouseY = event.clientY;
      cursorDot.style.left = `${mouseX}px`;
      cursorDot.style.top = `${mouseY}px`;
      cursorDot.style.opacity = '1';
      cursorRing.style.opacity = '1';
    });

    hoverTargets.forEach((element) => {
      element.addEventListener('mouseenter', () => cursorRing.classList.add('active'));
      element.addEventListener('mouseleave', () => cursorRing.classList.remove('active'));
    });

    const animateCursor = () => {
      ringX += (mouseX - ringX) * 0.18;
      ringY += (mouseY - ringY) * 0.18;
      cursorRing.style.left = `${ringX}px`;
      cursorRing.style.top = `${ringY}px`;
      requestAnimationFrame(animateCursor);
    };

    animateCursor();
  };

  setupCursor();
  applyIcon();

  const updateNavbar = () => {
    if (navbar) navbar.classList.toggle('navbar-scrolled', window.scrollY > 8);
  };
  updateNavbar();
  window.addEventListener('scroll', updateNavbar, { passive: true });

  if (toggle) {
    toggle.addEventListener('click', function () {
      const isDark = html.getAttribute('data-theme') === 'dark';
      const nextTheme = isDark ? 'light' : 'dark';
      html.setAttribute('data-theme', nextTheme);
      localStorage.setItem('retiya-theme', nextTheme);
      applyIcon();
    });
  }
});
