document.addEventListener('DOMContentLoaded', function () {
    const phoneInputField = document.querySelector("#id_phone_number");
    
    // --- Initialize International Telephone Input ---
    const phoneInput = window.intlTelInput(phoneInputField, {
        utilsScript: "https://cdnjs.cloudflare.com/ajax/libs/intl-tel-input/17.0.8/js/utils.js",
        initialCountry: "auto",
        geoIpLookup: function(callback) {
            fetch("https://ipapi.co/json")
              .then(res => res.json())
              .then(data => callback(data.country_code))
              .catch(() => callback("us"));
        },
        separateDialCode: true,
    });

    // --- View/Edit Mode Toggle Logic ---
    const viewMode = document.getElementById('profile-view-mode');
    const editMode = document.getElementById('profile-edit-mode');
    const editBtn = document.getElementById('edit-profile-btn');
    const cancelBtn = document.getElementById('cancel-edit-btn');

    if (editBtn) {
        editBtn.addEventListener('click', function() {
            viewMode.classList.add('d-none');
            editMode.classList.remove('d-none');
        });
    }

    if (cancelBtn) {
        cancelBtn.addEventListener('click', function() {
            editMode.classList.add('d-none');
            viewMode.classList.remove('d-none');
        });
    }
});
