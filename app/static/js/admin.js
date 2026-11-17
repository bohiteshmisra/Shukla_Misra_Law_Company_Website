// Admin panel: rich-text editors and delete confirmations.
(function () {
  document.querySelectorAll('[data-editor]').forEach(function (holder) {
    var field = document.getElementById(holder.getAttribute('data-editor'));
    if (!window.Quill || !field) return;
    var quill = new Quill(holder, {
      theme: 'snow',
      modules: { toolbar: [[{ header: [2, 3, false] }], ['bold', 'italic', 'underline'],
        [{ list: 'ordered' }, { list: 'bullet' }], ['blockquote', 'link'], ['clean']] }
    });
    quill.clipboard.dangerouslyPasteHTML(field.value || '');
    field.classList.add('d-none');
    field.form.addEventListener('submit', function () {
      var html = quill.getSemanticHTML().replace(/&nbsp;/g, ' ');
      field.value = quill.getText().trim() ? html : '';
    });
  });
  document.querySelectorAll('form[data-confirm]').forEach(function (form) {
    form.addEventListener('submit', function (event) {
      if (!window.confirm(form.getAttribute('data-confirm'))) event.preventDefault();
    });
  });
})();
