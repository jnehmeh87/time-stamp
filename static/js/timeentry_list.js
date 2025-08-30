document.addEventListener('DOMContentLoaded', function () {
  // --- Column Reordering & Persistence ---
  const headerRow = document.getElementById('sortable-headers');
  const tableBody = document.getElementById('table-body');
  const storageKey = 'timeEntryTableColumnOrder';

  // Function to apply a specific column order
  function applyColumnOrder(order) {
    if (!order || !tableBody || !headerRow) return;

    const headers = Array.from(headerRow.children);
    const newHeaderOrder = order
      .map((id) => headers.find((h) => h.dataset.columnId === id))
      .filter(Boolean); // .filter(Boolean) removes undefined
    headerRow.replaceChildren(...newHeaderOrder);

    Array.from(tableBody.rows).forEach((row) => {
      if (row.children.length > 1) {
        // Skip the "No entries found" row
        const cells = Array.from(row.children);
        const newCellOrder = order
          .map((id) => cells.find((c) => c.dataset.columnId === id))
          .filter(Boolean);
        row.replaceChildren(...newCellOrder);
      }
    });
  }

  // --- Smartly Load and Apply Column Order ---
  const savedOrder = JSON.parse(localStorage.getItem(storageKey));
  const currentColumns = Array.from(headerRow.children).map(
    (th) => th.dataset.columnId
  );

  // Check if the saved order is valid (same columns)
  const isOrderValid =
    savedOrder &&
    savedOrder.length === currentColumns.length &&
    savedOrder.every((id) => currentColumns.includes(id));

  if (isOrderValid) {
    applyColumnOrder(savedOrder);
  } else {
    // If order is invalid or doesn't exist, clear it from storage
    localStorage.removeItem(storageKey);
  }

  // Initialize SortableJS for drag-and-drop
  if (headerRow && typeof Sortable !== 'undefined') {
    new Sortable(headerRow, {
      animation: 150,
      onEnd: function () {
        const newOrder = Array.from(this.el.children).map(
          (th) => th.dataset.columnId
        );
        localStorage.setItem(storageKey, JSON.stringify(newOrder));
        applyColumnOrder(newOrder);
      },
    });
  }

  // --- View Toggler ---
  const tableViewBtn = document.getElementById('table-view-btn');
  const cardViewBtn = document.getElementById('card-view-btn');
  const tableContainer = document.getElementById('table-view-container');
  const cardContainer = document.getElementById('card-view-container');

  function setView(view) {
    if (view === 'card') {
      tableContainer.style.display = 'none';
      cardContainer.style.display = 'flex'; // Use flex for proper row wrapping
      tableViewBtn.classList.remove('active');
      cardViewBtn.classList.add('active');
      localStorage.setItem('timeEntryView', 'card');
    } else {
      tableContainer.style.display = 'block';
      cardContainer.style.display = 'none';
      tableViewBtn.classList.add('active');
      cardViewBtn.classList.remove('active');
      localStorage.setItem('timeEntryView', 'table');
    }
  }

  if (tableViewBtn && cardViewBtn && tableContainer && cardContainer) {
    tableViewBtn.addEventListener('click', () => setView('table'));
    cardViewBtn.addEventListener('click', () => setView('card'));

    // Restore user's preferred view on page load, or set default based on screen size
    const preferredView = localStorage.getItem('timeEntryView');
    if (preferredView) {
      setView(preferredView);
    } else {
      // If no preference is stored, default to card view on smaller screens (Bootstrap's lg breakpoint)
      if (window.innerWidth < 992) {
        setView('card');
      } else {
        setView('table'); // Default to table view on larger screens
      }
    }
  }

  // --- Mobile Filter Icon Toggle ---
  const filterCollapseElement = document.getElementById(
    'filter-collapse-mobile'
  );
  if (filterCollapseElement) {
    const toggleIcon = document.querySelector('.filter-toggle-icon');
    filterCollapseElement.addEventListener('show.bs.collapse', function () {
      toggleIcon.textContent = '−'; // Minus sign
    });
    filterCollapseElement.addEventListener('hide.bs.collapse', function () {
      toggleIcon.textContent = '+';
    });
  }

  // --- Dynamic Filter Logic ---
  function setupDynamicFilters(
    categorySelectEl,
    projectSelectEl,
    startDateIn,
    endDateIn
  ) {
    if (!categorySelectEl || !projectSelectEl) return;

    const projectOptions = Array.from(projectSelectEl.options);
    const projectDatesUrl = projectSelectEl.dataset.projectDatesUrl;

    // 1. Filter projects based on category
    categorySelectEl.addEventListener('change', function () {
      const selectedCategory = this.value;
      const currentProject = projectSelectEl.value;

      // Reset project dropdown
      projectSelectEl.innerHTML = '';

      projectOptions.forEach((option) => {
        if (
          option.value === '' ||
          selectedCategory === '' ||
          option.dataset.category === selectedCategory
        ) {
          projectSelectEl.add(option.cloneNode(true));
        }
      });

      // Restore selection if possible, otherwise reset
      const selectedOption = projectSelectEl.querySelector(
        `option[value="${currentProject}"]`
      );
      if (selectedOption) {
        projectSelectEl.value = currentProject;
      } else {
        projectSelectEl.value = '';
      }
    });

    // Trigger change on load to filter initial view
    categorySelectEl.dispatchEvent(new Event('change'));

    // 2. Auto-populate dates on project selection
    projectSelectEl.addEventListener('change', function () {
      const projectId = this.value;
      if (projectId && projectDatesUrl) {
        fetch(`${projectDatesUrl}?project_id=${projectId}`)
          .then((response) => response.json())
          .then((data) => {
            if (data.success) {
              if (startDateIn) startDateIn.value = data.start_date;
              if (endDateIn) endDateIn.value = data.end_date;
            }
          });
      }
    });
  }

  // Setup for desktop filters
  setupDynamicFilters(
    document.getElementById('category_desktop'),
    document.getElementById('project_desktop'),
    document.getElementById('start_date_desktop'),
    document.getElementById('end_date_desktop')
  );

  // Setup for mobile filters
  setupDynamicFilters(
    document.getElementById('category_mobile'),
    document.getElementById('project_mobile'),
    document.getElementById('start_date_mobile'),
    document.getElementById('end_date_mobile')
  );

  // --- Bulk Action Logic ---
  const selectAllCheckbox = document.getElementById('select-all-entries');
  // Select checkboxes from both views
  const entryCheckboxes = document.querySelectorAll('.entry-checkbox');
  const bulkDeleteBtn = document.getElementById('bulk-delete-btn');
  const bulkArchiveBtn = document.getElementById('bulk-archive-btn');
  const bulkUnarchiveBtn = document.getElementById('bulk-unarchive-btn');
  const bulkActionForm = document.getElementById('bulk-action-form');

  function toggleBulkActionButtons() {
    const anyChecked = Array.from(entryCheckboxes).some((cb) => cb.checked);
    if (bulkDeleteBtn) bulkDeleteBtn.disabled = !anyChecked;
    if (bulkArchiveBtn) bulkArchiveBtn.disabled = !anyChecked;
    if (bulkUnarchiveBtn) bulkUnarchiveBtn.disabled = !anyChecked;
  }

  if (selectAllCheckbox) {
    selectAllCheckbox.addEventListener('change', function () {
      entryCheckboxes.forEach((checkbox) => {
        checkbox.checked = selectAllCheckbox.checked;
      });
      toggleBulkActionButtons();
    });
  }

  entryCheckboxes.forEach((checkbox) => {
    checkbox.addEventListener('change', function () {
      if (!this.checked) {
        selectAllCheckbox.checked = false;
      } else {
        const allChecked = Array.from(entryCheckboxes).every(
          (cb) => cb.checked
        );
        if (allChecked) {
          selectAllCheckbox.checked = true;
        }
      }
      toggleBulkActionButtons();
    });
  });

  if (bulkActionForm) {
    bulkActionForm.addEventListener('submit', function (e) {
      const anyChecked = Array.from(entryCheckboxes).some((cb) => cb.checked);
      if (!anyChecked) {
        e.preventDefault();
        alert('Please select at least one entry.');
        return;
      }
    });
  }

  toggleBulkActionButtons(); // Initial check on page load

  // --- Entry Details Modal ---
  const entryDetailsModal = document.getElementById('entryDetailsModal');
  if (entryDetailsModal) {
    const modalSpinner = document.getElementById('modal-spinner');
    const modalContent = document.getElementById('modal-content-area');

    entryDetailsModal.addEventListener('show.bs.modal', function (event) {
      const button = event.relatedTarget;
      const entryId = button.dataset.entryId;

      // Show spinner, hide content
      modalSpinner.classList.remove('d-none');
      modalContent.classList.add('d-none');

      fetch(`/ajax/get-entry-details/${entryId}/`)
        .then((response) => response.json())
        .then((data) => {
          if (data.success) {
            // Populate modal
            document.getElementById('modal-title').textContent = data.title;
            document.getElementById('modal-project').textContent = data.project;
            document.getElementById('modal-category').textContent =
              data.category;
            document.getElementById('modal-start-time').textContent =
              data.start_time;
            document.getElementById('modal-end-time').textContent =
              data.end_time;
            document.getElementById('modal-duration').textContent =
              data.duration;
            document.getElementById('modal-pause').textContent =
              data.paused_duration;
            document.getElementById('modal-description').textContent =
              data.description;
            document.getElementById('modal-notes').textContent = data.notes;
            document.getElementById('modal-edit-button').href = data.update_url;

            const gallery = document.getElementById('modal-images-gallery');
            const imagesSection = document.getElementById(
              'modal-images-section'
            );
            gallery.innerHTML = ''; // Clear previous images

            if (data.images && data.images.length > 0) {
              data.images.forEach((img) => {
                const col = document.createElement('div');
                col.className = 'col-md-4 mb-3';
                col.innerHTML = `<a href="${img.url}" target="_blank"><img src="${img.url}" class="img-fluid rounded" alt="Entry Image"></a>`;
                gallery.appendChild(col);
              });
              imagesSection.classList.remove('d-none');
            } else {
              imagesSection.classList.add('d-none');
            }

            // Hide spinner, show content
            modalSpinner.classList.add('d-none');
            modalContent.classList.remove('d-none');
          } else {
            // Handle error
            document.getElementById(
              'modal-content-area'
            ).innerHTML = `<p class="text-danger">Error: ${data.error}</p>`;
            modalSpinner.classList.add('d-none');
            modalContent.classList.remove('d-none');
          }
        });
    });
  }
});
