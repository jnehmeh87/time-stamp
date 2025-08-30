function _translate(text) {
  return text;
}

$(document).ready(function () {
  $('.toast').toast('show');
  $('body').on('click', '.show-toast', function () {
    const toastId = $(this).data('toast-target');
    $(toastId).toast('show');
  });
});

document.addEventListener('DOMContentLoaded', function () {
  var popoverTriggerList = [].slice.call(
    document.querySelectorAll('[data-bs-toggle="popover"]')
  );
  popoverTriggerList.map(function (popoverTriggerEl) {
    return new bootstrap.Popover(popoverTriggerEl);
  });
});

// Auto-hide toast notifications
var toastElements = document.querySelectorAll('.toast-custom');
toastElements.forEach(function (toast) {
  setTimeout(function () {
    toast.classList.add('fade-out');
    // Optional: remove the element after fade out
    setTimeout(function () {
      if (toast.parentNode) {
        toast.parentNode.removeChild(toast);
      }
    }, 500); // Corresponds to the transition duration
  }, 5000); // 5 seconds
});
