document.addEventListener('DOMContentLoaded', function() {
    const socialLoginLinks = document.querySelectorAll('a[data-modal-url]');
    const modalElement = document.getElementById('social-login-modal');
    
    if (modalElement) {
        const socialModal = new bootstrap.Modal(modalElement);
        const modalBody = modalElement.querySelector('.modal-body');

        socialLoginLinks.forEach(function(link) {
            link.addEventListener('click', function(event) {
                event.preventDefault();
                const url = this.getAttribute('data-modal-url');

                fetch(url)
                    .then(response => response.text())
                    .then(html => {
                        if (modalBody) {
                            modalBody.innerHTML = html;
                            socialModal.show();
                        }
                    })
                    .catch(error => {
                        console.error('Error fetching social login content:', error);
                        // If fetching fails, fall back to standard redirect
                        window.location.href = url;
                    });
            });
        });
    }
});
