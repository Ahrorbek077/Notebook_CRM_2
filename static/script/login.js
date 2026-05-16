// 3D card tilt on mouse move (desktop only)
(function () {
  const card = document.querySelector('.login-card');
  if (!card || window.innerWidth < 768) return;

  const wrapper = document.querySelector('.login-wrapper');

  wrapper.addEventListener('mousemove', (e) => {
    const rect = wrapper.getBoundingClientRect();
    const cx = rect.left + rect.width / 2;
    const cy = rect.top + rect.height / 2;
    const dx = (e.clientX - cx) / (rect.width / 2);
    const dy = (e.clientY - cy) / (rect.height / 2);
    const rotX = -dy * 6;
    const rotY = dx * 6;
    card.style.transform = `perspective(900px) rotateX(${rotX}deg) rotateY(${rotY}deg) scale(1.015)`;
  });

  wrapper.addEventListener('mouseleave', () => {
    card.style.transform = 'perspective(900px) rotateX(0deg) rotateY(0deg) scale(1)';
  });
})();

// Password show/hide toggle
(function () {
  const btn = document.getElementById('pw-toggle-btn');
  const input = document.getElementById('id_password');
  if (!btn || !input) return;

  const eyeOpen = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" xmlns="http://www.w3.org/2000/svg"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>`;
  const eyeOff  = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" xmlns="http://www.w3.org/2000/svg"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>`;

  let visible = false;
  btn.innerHTML = eyeOpen;

  btn.addEventListener('click', () => {
    visible = !visible;
    input.type = visible ? 'text' : 'password';
    btn.innerHTML = visible ? eyeOff : eyeOpen;
    btn.setAttribute('aria-label', visible ? 'Hide password' : 'Show password');
  });
})();