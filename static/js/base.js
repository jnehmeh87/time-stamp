function translate(source, dest, source_lang, dest_lang, loading_gif_url) {
    $(dest).html('<img src="' + loading_gif_url + '">');
    $.post('/translate', {
        text: $(source).val(),
        source_language: source_lang,
        dest_language: dest_lang
    }).done(function(response) {
        $(dest).text(response['text'])
    }).fail(function() {
        $(dest).text("Error: Could not contact server.");
    });
}

document.addEventListener('DOMContentLoaded', function () {
    // Auto-hide toast notifications
    var toastElements = document.querySelectorAll('.toast-custom');
    toastElements.forEach(function(toast) {
        setTimeout(function() {
            toast.classList.add('fade-out');
            // Optional: remove the element after fade out
            setTimeout(function() {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 500); // Corresponds to the transition duration
        }, 5000); // 5 seconds
    });
});
