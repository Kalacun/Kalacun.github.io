// The complete page, links, and expanded research are usable without JavaScript.
const navLinks = [...document.querySelectorAll('.page-nav a[href^="#"]')];
const navSections = navLinks.map(link => document.getElementById(link.hash.slice(1))).filter(Boolean);
let scheduled = false;
function updateNavigation() {
  scheduled = false;
  let current = navSections[0];
  for (const section of navSections) {
    if (section.getBoundingClientRect().top <= 64) current = section;
  }
  if (scrollY > 0 && innerHeight + scrollY >= document.documentElement.scrollHeight - 4) current = navSections.at(-1);
  for (const link of navLinks) {
    if (link.hash === '#' + current?.id) link.setAttribute('aria-current', 'location');
    else link.removeAttribute('aria-current');
  }
}
function scheduleNavigation() {
  if (!scheduled) { scheduled = true; requestAnimationFrame(updateNavigation); }
}
addEventListener('scroll', scheduleNavigation, { passive: true });
addEventListener('resize', scheduleNavigation);
addEventListener('hashchange', scheduleNavigation);
document.addEventListener('toggle', scheduleNavigation, true);
updateNavigation();

let printState = null;
addEventListener('beforeprint', () => {
  if (printState) return;
  printState = [...document.querySelectorAll('details')].map(item => [item, item.open]);
  for (const [item] of printState) item.open = true;
});
addEventListener('afterprint', () => {
  for (const [item, open] of printState || []) item.open = open;
  printState = null;
});

// Optional local photo selection while editing. No upload or file changes.
for (const input of document.querySelectorAll('[data-photo-input]')) {
  input.addEventListener('change', () => {
    const file = input.files?.[0];
    if (!file) return;
    const status = input.closest('.photo-widget').querySelector('[data-photo-status]');
    if (!['image/jpeg','image/png','image/webp'].includes(file.type) || file.size > 8 * 1024 * 1024) {
      if (status) status.textContent = 'Choose a JPG, PNG, or WebP image under 8 MB.';
      input.value = '';
      return;
    }
    const reader = new FileReader();
    reader.addEventListener('load', () => {
      const widget = input.closest('.photo-widget');
      const picture = widget.querySelector('[data-profile-photo]');
      picture.src = reader.result;
      picture.hidden = false;
      widget.querySelector('.photo-fallback').hidden = true;
      if (status) status.textContent = 'Local photo preview · save the image in assets/ to keep it.';
    });
    reader.readAsDataURL(file);
  });
}
