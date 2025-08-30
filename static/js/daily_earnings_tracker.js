document.addEventListener('DOMContentLoaded', function () {
  // --- Logic for the filter button ---
  const filterCollapse = document.getElementById('filterCollapse');
  const filterButton = document.querySelector(
    '[data-bs-target="#filterCollapse"]'
  );
  const collapseIcon = document.getElementById('collapse-icon');

  const updateButton = () => {
    if (!filterButton) return;
    const isExpanded = filterButton.getAttribute('aria-expanded') === 'true';
    if (isExpanded) {
      filterButton.classList.remove('btn-primary');
      filterButton.classList.add('btn-secondary');
      if (collapseIcon) collapseIcon.textContent = '-';
    } else {
      filterButton.classList.remove('btn-secondary');
      filterButton.classList.add('btn-primary');
      if (collapseIcon) collapseIcon.textContent = '+';
    }
  };

  if (filterCollapse) {
    filterCollapse.addEventListener('shown.bs.collapse', updateButton);
    filterCollapse.addEventListener('hidden.bs.collapse', updateButton);
    // Set initial state
    updateButton();
  }

  // Logic for project date filtering
  const categorySelect = document.getElementById('id_category');
  const projectSelect = document.getElementById('id_project');

  if (categorySelect) {
    categorySelect.addEventListener('change', function () {
      if (projectSelect) projectSelect.value = '';
      const url = new URL(window.location);
      url.searchParams.set('category', this.value);
      url.searchParams.delete('project');
      // Keep other params
      url.searchParams.delete('start_date');
      url.searchParams.delete('end_date');
      window.location.href = url.toString();
    });
  }

  // Chart.js implementation
  try {
    const labelsEl = document.getElementById('chart-labels');
    const dataEl = document.getElementById('chart-data');
    const chartCanvas = document.getElementById('dailyEarningsChart');

    if (labelsEl && dataEl && chartCanvas) {
      const labels = JSON.parse(labelsEl.textContent);
      const data = JSON.parse(dataEl.textContent);

      if (labels.length > 0) {
        const ctx = chartCanvas.getContext('2d');
        new Chart(ctx, {
          type: 'bar',
          data: {
            labels: labels,
            datasets: [
              {
                label: 'Daily Earnings (SEK)',
                data: data,
                backgroundColor: 'rgba(0, 123, 255, 0.5)',
                borderColor: 'rgba(0, 123, 255, 1)',
                borderWidth: 1,
              },
            ],
          },
          options: {
            scales: {
              y: {
                beginAtZero: true,
                ticks: {
                  // Include a dollar sign in the ticks
                  callback: function (value, _index, _values) {
                    return '$' + value;
                  },
                },
              },
            },
            plugins: {
              tooltip: {
                callbacks: {
                  label: function (context) {
                    let label = context.dataset.label || '';
                    if (label) {
                      label += ': ';
                    }
                    if (context.parsed.y !== null) {
                      label += new Intl.NumberFormat('sv-SE', {
                        style: 'currency',
                        currency: 'SEK',
                      }).format(context.parsed.y);
                    }
                    return label;
                  },
                },
              },
            },
          },
        });
      }
    }
  } catch (e) {
    // Fail silently if chart data is not available or malformed
    console.error('Could not render chart:', e);
  }
});
