document.addEventListener('DOMContentLoaded', function() {
    // Load dashboard data
    if (document.getElementById('sentimentChart')) {
        fetch('/api/dashboard-data')
            .then(response => response.json())
            .then(data => {
                updateDashboard(data);
                setupEventListeners();
            });
    }

    function updateDashboard(data) {
        // Update sentiment chart
        const ctx = document.getElementById('sentimentChart').getContext('2d');
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.feedback_stats.map(item => item.location),
                datasets: [{
                    label: 'Average Sentiment',
                    data: data.feedback_stats.map(item => item.avg_sentiment),
                    backgroundColor: 'rgba(54, 162, 235, 0.5)',
                    borderColor: 'rgba(54, 162, 235, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                scales: {
                    y: {
                        beginAtZero: false,
                        min: -1,
                        max: 1
                    }
                }
            }
        });

        // Update polls
        const pollsContainer = document.getElementById('polls-container');
        if (pollsContainer) {
            pollsContainer.innerHTML = data.active_polls.map(poll => `
                <div class="card mb-3">
                    <div class="card-body">
                        <h5>${poll.question}</h5>
                        ${poll.options.map((option, index) => `
                            <div class="form-check mb-2">
                                <input class="form-check-input" type="radio"
                                    name="poll-${poll.id}"
                                    id="poll-${poll.id}-${index}">
                                <label class="form-check-label" for="poll-${poll.id}-${index}">
                                    ${option.text} (${option.votes || 0} votes)
                                </label>
                            </div>
                        `).join('')}
                        <button class="btn btn-primary btn-sm mt-2"
                            onclick="votePoll(${poll.id})">Vote</button>
                    </div>
                </div>
            `).join('');
        }

        // Update alerts
        const alertsContainer = document.getElementById('alerts-container');
        if (alertsContainer) {
            alertsContainer.innerHTML = data.recent_alerts.map(alert => `
                <div class="alert alert-${alert.severity === 'high' ? 'danger' : 'warning'}">
                    <strong>${alert.topic}</strong> - ${alert.severity} priority
                </div>
            `).join('');
        }
    }

    function setupEventListeners() {
        // Feedback form submission
        const feedbackForm = document.getElementById('feedbackForm');
        if (feedbackForm) {
            feedbackForm.addEventListener('submit', function(e) {
                e.preventDefault();

                const formData = {
                    content: this.querySelector('textarea').value,
                    location: this.querySelector('#location').value,
                    gender: this.querySelector('#gender').value
                };

                fetch('/api/feedback', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(formData)
                })
                .then(response => response.json())
                .then(data => {
                    alert('Feedback submitted successfully!');
                    this.reset();
                });
            });
        }
    }

    // Global function for voting
    window.votePoll = function(pollId) {
        const selectedOption = document.querySelector(
            `input[name="poll-${pollId}"]:checked`);

        if (!selectedOption) {
            alert('Please select an option');
            return;
        }

        const optionIndex = selectedOption.id.split('-').pop();

        fetch(`/api/polls/${pollId}/vote`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ option_index: parseInt(optionIndex) })
        })
        .then(response => response.json())
        .then(data => {
            alert('Vote recorded!');
            window.location.reload();
        });
    };
});