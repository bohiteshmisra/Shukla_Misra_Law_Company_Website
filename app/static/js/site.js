// Disclaimer pop-up required by ICAI guidelines: shown until the visitor agrees.
(function () {
  var KEY = 'smc-disclaimer-accepted';
  var el = document.getElementById('disclaimerModal');
  if (!el || !window.bootstrap) return;
  var accepted = false;
  try { accepted = window.localStorage.getItem(KEY) === 'yes'; } catch (e) { /* storage unavailable */ }
  if (accepted || /\/disclaimer$/.test(window.location.pathname)) return;
  var modal = new bootstrap.Modal(el);
  modal.show();
  document.getElementById('disclaimerAgree').addEventListener('click', function () {
    try { window.localStorage.setItem(KEY, 'yes'); } catch (e) { /* ignore */ }
    modal.hide();
  });
})();
