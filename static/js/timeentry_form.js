document.addEventListener('DOMContentLoaded', function () {
  const editTimeBtn = document.getElementById('edit-time-btn');
  const timeDisplay = document.getElementById('time-details-display');
  const timeEdit = document.getElementById('time-details-edit');
  const timeEditedFlag = document.getElementById('time_details_edited_flag');

  // For new entries (where the edit button doesn't exist), the edit section is visible by default.
  // We must set the flag to true so the view knows it's a manual time entry.
  if (!editTimeBtn) {
    if (timeEditedFlag) {
      timeEditedFlag.value = 'true';
    }
    return;
  }

  // For existing entries, clicking the button reveals the fields and sets the flag.
  editTimeBtn.addEventListener('click', function () {
    timeDisplay.classList.add('d-none');
    timeEdit.classList.remove('d-none');
    timeEditedFlag.value = 'true';
  });
});
