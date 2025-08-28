$(document).ready(function() {
    // Time details edit toggle
    const editTimeBtn = document.getElementById('edit-time-btn');
    if (editTimeBtn) {
        editTimeBtn.addEventListener('click', function() {
            document.getElementById('time-details-display').classList.add('d-none');
            document.getElementById('time-details-edit').classList.remove('d-none');
            document.getElementById('time_details_edited_flag').value = 'true';
        });
    }

    // Image deletion
    const imageContainer = document.getElementById('existing-images-container');
    if (imageContainer) {
        imageContainer.addEventListener('click', function(event) {
            if (event.target.classList.contains('delete-image-btn')) {
                const imageId = event.target.dataset.imageId;
                if (confirm('Are you sure you want to delete this image?')) {
                    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
                    fetch(`/ajax/delete-image/${imageId}/`, {
                        method: 'POST',
                        headers: {
                            'X-CSRFToken': csrfToken,
                            'Content-Type': 'application/json'
                        }
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            const imageElement = document.getElementById(`image-container-${imageId}`);
                            if (imageElement) {
                                imageElement.remove();
                            }
                        } else {
                            alert('Error deleting image: ' + data.error);
                        }
                    });
                }
            }
        });
    }
});
