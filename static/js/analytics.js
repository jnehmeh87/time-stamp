document.addEventListener('DOMContentLoaded', function () {
  // Helper to generate random colors
  const generateColors = (numColors) => {
    const colors = [];
    for (let i = 0; i < numColors; i++) {
      const r = Math.floor(Math.random() * 200);
      const g = Math.floor(Math.random() * 200);
      const b = Math.floor(Math.random() * 200);
      colors.push(`rgba(${r}, ${g}, ${b}, 0.7)`);
    }
    return colors;
  };

  // 1. Category Doughnut Chart
  try {
    const categoryLabelsEl = document.getElementById('category_chart_labels');
    const categoryDataEl = document.getElementById('category_chart_data');
    if (categoryLabelsEl && categoryDataEl) {
      const categoryLabels = JSON.parse(categoryLabelsEl.textContent);
      const categoryData = JSON.parse(categoryDataEl.textContent);
      if (categoryData.length > 0) {
        new Chart(document.getElementById('categoryDoughnutChart'), {
          type: 'doughnut',
          data: {
            labels: categoryLabels,
            datasets: [
              {
                label: 'Hours',
                data: categoryData,
                backgroundColor: generateColors(categoryData.length),
                hoverOffset: 4,
              },
            ],
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
          },
        });
      }
    }
  } catch (e) {
    console.error('Error rendering category chart:', e);
  }

  // 2. Earnings Bar Chart
  try {
    const earningsLabelsEl = document.getElementById('earnings_chart_labels');
    const earningsDataEl = document.getElementById('earnings_chart_data');
    if (earningsLabelsEl && earningsDataEl) {
      const earningsLabels = JSON.parse(earningsLabelsEl.textContent);
      const earningsData = JSON.parse(earningsDataEl.textContent);
      if (earningsData.length > 0) {
        new Chart(document.getElementById('earningsBarChart'), {
          type: 'bar',
          data: {
            labels: earningsLabels,
            datasets: [
              {
                label: 'Total Earnings (SEK)',
                data: earningsData,
                backgroundColor: generateColors(earningsData.length),
              },
            ],
          },
          options: {
            responsive: true,
            scales: { y: { beginAtZero: true } },
          },
        });
      }
    }
  } catch (e) {
    console.error('Error rendering earnings chart:', e);
  }

  // 3. Activity Line Chart
  let activityChart; // Make chart instance accessible
  try {
    const activityLabelsEl = document.getElementById('activity_chart_labels');
    const activityDatasetsEl = document.getElementById(
      'activity_chart_datasets'
    );
    if (activityLabelsEl && activityDatasetsEl) {
      const activityLabels = JSON.parse(activityLabelsEl.textContent);
      const activityDatasets = JSON.parse(activityDatasetsEl.textContent);

      if (activityDatasets && activityDatasets.length > 0) {
        const lineColors = generateColors(activityDatasets.length);
        const datasetsForChart = activityDatasets.map((dataset, index) => {
          const color = lineColors[index];
          return {
            label: dataset.label,
            data: dataset.data,
            fill: false, // Set to false to see individual lines clearly
            borderColor: color,
            originalBorderColor: color, // Store the original color
            backgroundColor: color, // For legend and tooltips
            borderWidth: 2,
            originalBorderWidth: 2,
            tension: 0.1,
            pointRadius: 2, // Make points smaller
            pointHoverRadius: 5, // Enlarge points on hover
          };
        });

        activityChart = new Chart(
          document.getElementById('activityLineChart'),
          {
            type: 'line',
            data: {
              labels: activityLabels,
              datasets: datasetsForChart,
            },
            options: {
              responsive: true,
              maintainAspectRatio: false,
              scales: {
                y: {
                  beginAtZero: true,
                  max: 24,
                  title: {
                    display: true,
                    text: 'Hours',
                  },
                },
              },
              plugins: {
                legend: {
                  labels: {
                    // This filter function prevents duplicate labels in the legend
                    filter: function (item, chart) {
                      // Logic to only show the first instance of each label
                      return (
                        chart.datasets
                          .map((d) => d.label)
                          .indexOf(item.text) === item.datasetIndex
                      );
                    },
                  },
                  onClick: (e, legendItem, legend) => {
                    const chart = legend.chart;
                    const index = legendItem.datasetIndex;
                    const isFocused = chart.focusedDatasetIndex === index;

                    if (isFocused) {
                      // If clicking the currently focused item, reset all lines
                      chart.focusedDatasetIndex = null; // Clear focus
                      chart.data.datasets.forEach((ds) => {
                        ds.borderColor = ds.originalBorderColor;
                        ds.backgroundColor = ds.originalBorderColor;
                        ds.borderWidth = ds.originalBorderWidth;
                      });
                    } else {
                      // If clicking a new item, focus it and dim others
                      chart.focusedDatasetIndex = index; // Set focus
                      chart.data.datasets.forEach((ds, i) => {
                        // Use a robust way to create colors to avoid errors
                        const invisibleLineColor = ds.originalBorderColor
                          ? ds.originalBorderColor.replace(/, ?0.7\)/, ', 0)')
                          : 'rgba(0,0,0,0)';
                        const dimmedLegendColor = ds.originalBorderColor
                          ? ds.originalBorderColor.replace(/, ?0.7\)/, ', 0.2)')
                          : 'rgba(100,100,100,0.2)';

                        if (i === index) {
                          ds.borderColor = ds.originalBorderColor; // Full opacity
                          ds.backgroundColor = ds.originalBorderColor;
                          ds.borderWidth = 4; // Highlight with thicker line
                        } else {
                          // Make line invisible but keep legend icon dimmed
                          ds.borderColor = invisibleLineColor;
                          ds.backgroundColor = dimmedLegendColor;
                          ds.borderWidth = 2;
                        }
                      });
                    }
                    chart.update('none'); // Use 'none' to disable animation for faster updates
                  },
                },
              },
            },
          }
        );
      }
    }
  } catch (e) {
    console.error('Error rendering activity chart:', e);
  }

  // AJAX for category filter
  document.querySelectorAll('.category-filter-item').forEach((item) => {
    item.addEventListener('click', function (e) {
      e.preventDefault(); // Prevent default link navigation

      const _category = this.dataset.category;
      const url = new URL(this.href); // Use the href to construct the new URL

      // Add a header to signify an AJAX request
      fetch(url.toString(), {
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
        },
      })
        .then((response) => response.json())
        .then((data) => {
          // Update chart data
          if (activityChart && data.activity_chart_datasets) {
            const newDatasets = data.activity_chart_datasets;
            const lineColors = generateColors(newDatasets.length);
            activityChart.data.labels = data.activity_chart_labels;
            activityChart.data.datasets = newDatasets.map((dataset, index) => {
              const color = lineColors[index];
              return {
                label: dataset.label,
                data: dataset.data,
                fill: false,
                borderColor: color,
                originalBorderColor: color,
                backgroundColor: color,
                borderWidth: 2,
                originalBorderWidth: 2,
                tension: 0.1,
                pointRadius: 2,
                pointHoverRadius: 5,
              };
            });
            activityChart.update();
          }

          // Update the URL in the browser
          history.pushState({}, '', url);

          // Update the dropdown button text
          document.getElementById(
            'category-filter-btn'
          ).innerHTML = `<i class="fas fa-filter me-1"></i> ${this.textContent}`;

          // Update active state on filter items
          document
            .querySelectorAll('.category-filter-item')
            .forEach((el) => el.classList.remove('active'));
          this.classList.add('active');

          // Scroll to the chart
          document
            .getElementById('activity-chart-card')
            .scrollIntoView({ behavior: 'smooth' });
        })
        .catch((error) => console.error('Error fetching chart data:', error));
    });
  });

  document
    .getElementById('download-report-button')
    .addEventListener('click', function () {
      // Get selected category
      const categorySelect = document.getElementById('category-select');
      const _category =
        categorySelect.options[categorySelect.selectedIndex].value;

      // Get selected date range
      const dateRange = document.getElementById('date-range-picker').value;

      // Prepare the data for download
      const data = {
        category: _category,
        date_range: dateRange,
      };

      // Send the data to the server or handle the download
      console.log('Download report with data:', data);
      // Implement the download logic here
    });
});
