document.addEventListener('DOMContentLoaded', function() {
    const categorySelect = document.getElementById('id_category');
    const projectSelect = document.getElementById('id_project');
    const startDateInput = document.getElementById('id_start_date');
    const endDateInput = document.getElementById('id_end_date');
    const reportForm = document.getElementById('reportForm');

    if (categorySelect && reportForm) {
        categorySelect.addEventListener('change', function() {
            // Clear project selection and submit the form to reload the project dropdown
            if (projectSelect) {
                projectSelect.value = '';
            }
            reportForm.submit();
        });
    }

    if (projectSelect) {
        const projectDatesUrl = projectSelect.dataset.projectDatesUrl;
        projectSelect.addEventListener('change', function() {
            const projectId = this.value;
            if (projectId && projectDatesUrl) {
                fetch(`${projectDatesUrl}?project_id=${projectId}`)
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            if (startDateInput) startDateInput.value = data.start_date;
                            if (endDateInput) endDateInput.value = data.end_date;
                        }
                    });
            }
        });
    }
});
