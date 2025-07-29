document.addEventListener('DOMContentLoaded', function() {
    // Load dashboard data
    if (document.getElementById('sentimentChart')) {
        loadDashboardData();
    }

    // Load polls data separately
    if (document.getElementById('polls-container')) {
        loadPolls();
    }

    // Setup event listeners
    setupEventListeners();

    function loadDashboardData() {
        fetch('/api/dashboard-data')
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                console.log('Dashboard data loaded:', data);
                updateDashboard(data);
            })
            .catch(error => {
                console.error('Error loading dashboard data:', error);
            });
    }

    function loadPolls() {
        fetch('/api/polls')
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                console.log('Polls data loaded:', data);
                updatePolls(data.polls || []);
            })
            .catch(error => {
                console.error('Error loading polls:', error);
                document.getElementById('polls-container').innerHTML =
                    '<div class="alert alert-warning">Failed to load polls</div>';
            });
    }

    function updateDashboard(data) {
        // Update sentiment chart if data exists
        if (data.feedback_stats && data.feedback_stats.length > 0) {
            updateSentimentChart(data.feedback_stats);
        }

        // Update alerts
        updateAlerts(data.recent_alerts || []);

        // Update statistics
        updateStatistics(data);
    }

    function updateSentimentChart(feedbackStats) {
        const ctx = document.getElementById('sentimentChart');
        if (!ctx) return;

        new Chart(ctx.getContext('2d'), {
            type: 'bar',
            data: {
                labels: feedbackStats.map(item => item.location || 'Unknown'),
                datasets: [{
                    label: 'Average Sentiment',
                    data: feedbackStats.map(item => item.avg_sentiment || 0),
                    backgroundColor: feedbackStats.map(item => {
                        const sentiment = item.avg_sentiment || 0;
                        if (sentiment > 0.1) return 'rgba(75, 192, 192, 0.6)'; // Green for positive
                        if (sentiment < -0.1) return 'rgba(255, 99, 132, 0.6)'; // Red for negative
                        return 'rgba(255, 206, 86, 0.6)'; // Yellow for neutral
                    }),
                    borderColor: feedbackStats.map(item => {
                        const sentiment = item.avg_sentiment || 0;
                        if (sentiment > 0.1) return 'rgba(75, 192, 192, 1)';
                        if (sentiment < -0.1) return 'rgba(255, 99, 132, 1)';
                        return 'rgba(255, 206, 86, 1)';
                    }),
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: false,
                        min: -1,
                        max: 1,
                        ticks: {
                            callback: function(value) {
                                if (value > 0.1) return 'Positive';
                                if (value < -0.1) return 'Negative';
                                return 'Neutral';
                            }
                        }
                    }
                },
                plugins: {
                    title: {
                        display: true,
                        text: 'Citizen Sentiment by Location'
                    }
                }
            }
        });
    }

    function updatePolls(polls) {
        const pollsContainer = document.getElementById('polls-container');
        if (!pollsContainer) return;

        if (!polls || polls.length === 0) {
            pollsContainer.innerHTML = '<div class="alert alert-info">No active polls available</div>';
            return;
        }

        pollsContainer.innerHTML = polls.map(poll => {
            const totalVotes = poll.total_votes || 0;
            return `
                <div class="card mb-3" id="poll-${poll.id}">
                    <div class="card-body">
                        <h5 class="card-title">${escapeHtml(poll.question)}</h5>
                        <p class="text-muted small">Total votes: ${totalVotes}</p>
                        <div class="poll-options" id="poll-options-${poll.id}">
                            ${poll.options.map((option, index) => {
                                const percentage = option.percentage || 0;
                                const votes = option.votes || 0;
                                return `
                                    <div class="form-check mb-2">
                                        <input class="form-check-input" type="radio"
                                            name="poll-${poll.id}"
                                            id="poll-${poll.id}-option-${option.id || index}"
                                            value="${option.id || (index + 1)}">
                                        <label class="form-check-label d-flex justify-content-between"
                                               for="poll-${poll.id}-option-${option.id || index}">
                                            <span>${escapeHtml(option.text)}</span>
                                            <span class="badge bg-secondary">${votes} votes (${percentage.toFixed(1)}%)</span>
                                        </label>
                                        <div class="progress mt-1" style="height: 5px;">
                                            <div class="progress-bar" role="progressbar"
                                                 style="width: ${percentage}%"
                                                 aria-valuenow="${percentage}"
                                                 aria-valuemin="0"
                                                 aria-valuemax="100"></div>
                                        </div>
                                    </div>
                                `;
                            }).join('')}
                        </div>
                        <button class="btn btn-primary btn-sm mt-3"
                                onclick="votePoll(${poll.id})"
                                id="vote-btn-${poll.id}">
                            Submit Vote
                        </button>
                        <div id="vote-message-${poll.id}" class="mt-2"></div>
                    </div>
                </div>
            `;
        }).join('');
    }

    function updateAlerts(alerts) {
        const alertsContainer = document.getElementById('alerts-container');
        if (!alertsContainer) return;

        if (!alerts || alerts.length === 0) {
            alertsContainer.innerHTML = '<div class="alert alert-info">No recent alerts</div>';
            return;
        }

        alertsContainer.innerHTML = alerts.map(alert => `
            <div class="alert alert-${getSeverityClass(alert.severity)} alert-dismissible fade show">
                <strong>${escapeHtml(alert.topic)}</strong> - ${alert.severity} priority
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `).join('');
    }

    function updateStatistics(data) {
        // Update various statistics on the dashboard
        const statElements = {
            'total-users': data.total_users,
            'total-feedback': data.total_feedback,
            'total-issues': data.total_issues,
            'officials-count': data.officials_count
        };

        Object.entries(statElements).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = value || 0;
            }
        });
    }

    function setupEventListeners() {
        // Feedback form submission
        const feedbackForm = document.getElementById('feedbackForm');
        if (feedbackForm) {
            feedbackForm.addEventListener('submit', handleFeedbackSubmission);
        }

        // Issue creation form
        const issueForm = document.getElementById('issueForm');
        if (issueForm) {
            issueForm.addEventListener('submit', handleIssueSubmission);
        }

        // Issue search form
        const issueSearchForm = document.getElementById('issueSearchForm');
        if (issueSearchForm) {
            issueSearchForm.addEventListener('submit', handleIssueSearch);
        }

        // Load issues on page load
        if (document.getElementById('issues-container')) {
            loadIssues();
        }
    }

    function handleFeedbackSubmission(e) {
        e.preventDefault();

        const submitBtn = this.querySelector('button[type="submit"]');
        const originalText = submitBtn.textContent;
        submitBtn.disabled = true;
        submitBtn.textContent = 'Submitting...';

        const formData = {
            content: this.querySelector('#feedbackContent').value.trim(),
            location: this.querySelector('#location')?.value || '',
            gender: this.querySelector('#gender')?.value || '',
            contact: this.querySelector('#contact')?.value || '',
            language: this.querySelector('#language')?.value || 'en',
            source: 'web'
        };

        // Validate required fields
        if (!formData.content) {
            showMessage('feedback-message', 'Please enter your feedback', 'danger');
            submitBtn.disabled = false;
            submitBtn.textContent = originalText;
            return;
        }

        console.log('Submitting feedback:', formData);

        fetch('/api/feedback', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        })
        .then(response => {
            console.log('Feedback response status:', response.status);
            if (!response.ok) {
                return response.json().then(err => Promise.reject(err));
            }
            return response.json();
        })
        .then(data => {
            console.log('Feedback submitted successfully:', data);
            showMessage('feedback-message', 'Feedback submitted successfully! Thank you for your input.', 'success');
            this.reset();

            // Reload dashboard data to reflect new feedback
            setTimeout(() => {
                loadDashboardData();
            }, 1000);
        })
        .catch(error => {
            console.error('Error submitting feedback:', error);
            showMessage('feedback-message',
                'Error submitting feedback: ' + (error.error || error.message || 'Please try again'),
                'danger');
        })
        .finally(() => {
            submitBtn.disabled = false;
            submitBtn.textContent = originalText;
        });
    }

    function handleIssueSubmission(e) {
        e.preventDefault();

        const submitBtn = this.querySelector('button[type="submit"]');
        const originalText = submitBtn.textContent;
        submitBtn.disabled = true;
        submitBtn.textContent = 'Creating...';

        const formData = {
            title: this.querySelector('#issueTitle').value.trim(),
            description: this.querySelector('#issueDescription').value.trim(),
            location: this.querySelector('#issueLocation').value.trim(),
            category: this.querySelector('#issueCategory')?.value || 'General',
            priority: this.querySelector('#issuePriority')?.value || 'Medium',
            contact: this.querySelector('#issueContact')?.value || '',
            user_id: 'anonymous' // You can get this from current user if logged in
        };

        // Validate required fields
        if (!formData.title || !formData.description || !formData.location) {
            showMessage('issue-message', 'Please fill in all required fields', 'danger');
            submitBtn.disabled = false;
            submitBtn.textContent = originalText;
            return;
        }

        console.log('Creating issue:', formData);

        fetch('/api/issues', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        })
        .then(response => {
            console.log('Issue response status:', response.status);
            if (!response.ok) {
                return response.json().then(err => Promise.reject(err));
            }
            return response.json();
        })
        .then(data => {
            console.log('Issue created successfully:', data);
            showMessage('issue-message',
                `Issue created successfully! Reference ID: ${data.issue_id}`,
                'success');
            this.reset();

            // Reload issues list if available
            if (document.getElementById('issues-container')) {
                loadIssues();
            }
        })
        .catch(error => {
            console.error('Error creating issue:', error);
            showMessage('issue-message',
                'Error creating issue: ' + (error.error || error.message || 'Please try again'),
                'danger');
        })
        .finally(() => {
            submitBtn.disabled = false;
            submitBtn.textContent = originalText;
        });
    }

    function handleIssueSearch(e) {
        e.preventDefault();
        const searchTerm = this.querySelector('#searchTerm').value.trim();
        const location = this.querySelector('#searchLocation')?.value || '';
        const status = this.querySelector('#searchStatus')?.value || 'Open';

        loadIssues(searchTerm, location, status);
    }

    function loadIssues(search = '', location = '', status = 'Open') {
        const container = document.getElementById('issues-container');
        if (!container) return;

        container.innerHTML = '<div class="text-center"><div class="spinner-border" role="status"></div></div>';

        const params = new URLSearchParams();
        if (search) params.append('search', search);
        if (location) params.append('location', location);
        if (status !== 'all') params.append('status', status);

        fetch(`/api/issues?${params.toString()}`)
            .then(response => {
                if (!response.ok) throw new Error('Failed to load issues');
                return response.json();
            })
            .then(data => {
                console.log('Issues loaded:', data);
                displayIssues(data.issues || []);
            })
            .catch(error => {
                console.error('Error loading issues:', error);
                container.innerHTML = '<div class="alert alert-danger">Failed to load issues</div>';
            });
    }

    function displayIssues(issues) {
        const container = document.getElementById('issues-container');
        if (!container) return;

        if (issues.length === 0) {
            container.innerHTML = '<div class="alert alert-info">No issues found</div>';
            return;
        }

        container.innerHTML = issues.map(issue => `
            <div class="card mb-3">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-start">
                        <h5 class="card-title">${escapeHtml(issue.title)}</h5>
                        <span class="badge bg-${getPriorityClass(issue.priority)}">${issue.priority}</span>
                    </div>
                    <p class="card-text">${escapeHtml(issue.description.substring(0, 150))}${issue.description.length > 150 ? '...' : ''}</p>
                    <div class="row">
                        <div class="col-md-6">
                            <small class="text-muted">
                                <i class="bi bi-geo-alt"></i> ${escapeHtml(issue.location)}
                            </small>
                        </div>
                        <div class="col-md-6">
                            <small class="text-muted">
                                <i class="bi bi-calendar"></i> ${new Date(issue.created_at).toLocaleDateString()}
                            </small>
                        </div>
                    </div>
                    <div class="mt-2">
                        <span class="badge bg-${getStatusClass(issue.status)}">${issue.status}</span>
                        <span class="badge bg-secondary">${issue.category}</span>
                        ${issue.feedback_count ? `<span class="badge bg-info">${issue.feedback_count} feedback</span>` : ''}
                    </div>
                    <button class="btn btn-sm btn-outline-primary mt-2"
                            onclick="viewIssueDetails(${issue.id})">
                        View Details
                    </button>
                </div>
            </div>
        `).join('');
    }

    // Global function for voting - FIXED VERSION
    window.votePoll = function(pollId) {
        const selectedOption = document.querySelector(`input[name="poll-${pollId}"]:checked`);
        const messageDiv = document.getElementById(`vote-message-${pollId}`);
        const voteBtn = document.getElementById(`vote-btn-${pollId}`);

        if (!selectedOption) {
            showMessage(`vote-message-${pollId}`, 'Please select an option', 'warning');
            return;
        }

        const optionId = parseInt(selectedOption.value);
        console.log(`Voting on poll ${pollId}, option ${optionId}`);

        // Disable vote button
        voteBtn.disabled = true;
        voteBtn.textContent = 'Submitting...';

        fetch(`/api/polls/${pollId}/vote`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ option_id: optionId })
        })
        .then(response => {
            console.log('Vote response status:', response.status);
            if (!response.ok) {
                return response.json().then(err => Promise.reject(err));
            }
            return response.json();
        })
        .then(data => {
            console.log('Vote response:', data);
            if (data.status === 'success') {
                showMessage(`vote-message-${pollId}`, 'Vote recorded successfully!', 'success');

                // Update the poll display with new results
                if (data.updated_poll) {
                    updateSinglePoll(pollId, data.updated_poll);
                }

                // Disable further voting on this poll
                const pollOptions = document.querySelectorAll(`input[name="poll-${pollId}"]`);
                pollOptions.forEach(option => option.disabled = true);
                voteBtn.style.display = 'none';
            } else {
                throw new Error(data.error || 'Failed to record vote');
            }
        })
        .catch(error => {
            console.error('Error voting:', error);
            showMessage(`vote-message-${pollId}`,
                'Error: ' + (error.error || error.message || 'Failed to record vote'),
                'danger');
            voteBtn.disabled = false;
            voteBtn.textContent = 'Submit Vote';
        });
    };

    function updateSinglePoll(pollId, updatedPoll) {
        const pollContainer = document.getElementById(`poll-options-${pollId}`);
        if (!pollContainer) return;

        const totalVotes = updatedPoll.total_votes || 0;

        updatedPoll.options.forEach((option, index) => {
            const optionElement = document.getElementById(`poll-${pollId}-option-${option.id || index}`);
            if (optionElement) {
                const label = optionElement.nextElementSibling;
                const badge = label.querySelector('.badge');
                const progressBar = label.parentElement.nextElementSibling.querySelector('.progress-bar');

                if (badge) {
                    badge.textContent = `${option.votes} votes (${option.percentage.toFixed(1)}%)`;
                }
                if (progressBar) {
                    progressBar.style.width = `${option.percentage}%`;
                    progressBar.setAttribute('aria-valuenow', option.percentage);
                }
            }
        });

        // Update total votes display
        const pollCard = document.getElementById(`poll-${pollId}`);
        const totalVotesElement = pollCard.querySelector('.text-muted');
        if (totalVotesElement) {
            totalVotesElement.textContent = `Total votes: ${totalVotes}`;
        }
    }

    window.viewIssueDetails = function(issueId) {
        // This can be expanded to show issue details in a modal or navigate to details page
        window.location.href = `/issues/${issueId}`;
    };

    // Utility functions
    function escapeHtml(text) {
        if (!text) return '';
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.replace(/[&<>"']/g, function(m) { return map[m]; });
    }

    function showMessage(elementId, message, type = 'info') {
        const element = document.getElementById(elementId);
        if (!element) {
            // Create message element if it doesn't exist
            const container = document.querySelector('.container') || document.body;
            const messageDiv = document.createElement('div');
            messageDiv.id = elementId;
            container.appendChild(messageDiv);
            return showMessage(elementId, message, type);
        }

        element.innerHTML = `
            <div class="alert alert-${type} alert-dismissible fade show" role="alert">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;

        // Auto-hide success messages
        if (type === 'success') {
            setTimeout(() => {
                element.innerHTML = '';
            }, 5000);
        }
    }

    function getSeverityClass(severity) {
        const severityMap = {
            'high': 'danger',
            'medium': 'warning',
            'low': 'info'
        };
        return severityMap[severity?.toLowerCase()] || 'info';
    }

    function getPriorityClass(priority) {
        const priorityMap = {
            'High': 'danger',
            'Medium': 'warning',
            'Low': 'info'
        };
        return priorityMap[priority] || 'secondary';
    }

    function getStatusClass(status) {
        const statusMap = {
            'Open': 'success',
            'In Progress': 'warning',
            'Closed': 'secondary',
            'Resolved': 'primary'
        };
        return statusMap[status] || 'secondary';
    }

    // Fixed poll rendering and voting functions - Add this to your dashboard.js

function updatePolls(polls) {
    const pollsContainer = document.getElementById('polls-container');
    if (!pollsContainer) return;

    if (!polls || polls.length === 0) {
        pollsContainer.innerHTML = '<div class="alert alert-info">No active polls available</div>';
        return;
    }

    pollsContainer.innerHTML = polls.map(poll => {
        const totalVotes = poll.total_votes || 0;
        return `
            <div class="card mb-3" id="poll-${poll.id}">
                <div class="card-body">
                    <h5 class="card-title">${escapeHtml(poll.question)}</h5>
                    <p class="text-muted small">Total votes: ${totalVotes}</p>
                    <div class="poll-options" id="poll-options-${poll.id}">
                        ${poll.options.map((option, index) => {
                            // Use option.id if available, otherwise use index + 1
                            const optionId = option.id || (index + 1);
                            const percentage = option.percentage || 0;
                            const votes = option.votes || 0;
                            return `
                                <div class="form-check mb-2">
                                    <input class="form-check-input" type="radio"
                                        name="poll-${poll.id}"
                                        id="poll-${poll.id}-option-${optionId}"
                                        value="${optionId}">
                                    <label class="form-check-label d-flex justify-content-between"
                                           for="poll-${poll.id}-option-${optionId}">
                                        <span>${escapeHtml(option.text)}</span>
                                        <span class="badge bg-secondary">${votes} votes (${percentage.toFixed(1)}%)</span>
                                    </label>
                                    <div class="progress mt-1" style="height: 5px;">
                                        <div class="progress-bar" role="progressbar"
                                             style="width: ${percentage}%"
                                             aria-valuenow="${percentage}"
                                             aria-valuemin="0"
                                             aria-valuemax="100"></div>
                                    </div>
                                </div>
                            `;
                        }).join('')}
                    </div>
                    <button class="btn btn-primary btn-sm mt-3"
                            onclick="votePoll(${poll.id})"
                            id="vote-btn-${poll.id}">
                        Submit Vote
                    </button>
                    <div id="vote-message-${poll.id}" class="mt-2"></div>
                </div>
            </div>
        `;
    }).join('');
}

// Fixed voting function
window.votePoll = function(pollId) {
    const selectedOption = document.querySelector(`input[name="poll-${pollId}"]:checked`);
    const messageDiv = document.getElementById(`vote-message-${pollId}`);
    const voteBtn = document.getElementById(`vote-btn-${pollId}`);

    if (!selectedOption) {
        showMessage(`vote-message-${pollId}`, 'Please select an option', 'warning');
        return;
    }

    const optionId = parseInt(selectedOption.value);
    console.log(`Voting on poll ${pollId}, option ${optionId}`);

    // Disable vote button
    voteBtn.disabled = true;
    voteBtn.textContent = 'Submitting...';

    fetch(`/api/polls/${pollId}/vote`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ option_id: optionId })
    })
    .then(response => {
        console.log('Vote response status:', response.status);
        if (!response.ok) {
            return response.json().then(err => Promise.reject(err));
        }
        return response.json();
    })
    .then(data => {
        console.log('Vote response:', data);
        if (data.status === 'success') {
            showMessage(`vote-message-${pollId}`, 'Vote recorded successfully!', 'success');

            // Update the poll display with new results
            if (data.updated_poll) {
                updateSinglePoll(pollId, data.updated_poll);
            }

            // Disable further voting on this poll
            const pollOptions = document.querySelectorAll(`input[name="poll-${pollId}"]`);
            pollOptions.forEach(option => option.disabled = true);
            voteBtn.style.display = 'none';
        } else {
            throw new Error(data.error || 'Failed to record vote');
        }
    })
    .catch(error => {
        console.error('Error voting:', error);
        showMessage(`vote-message-${pollId}`,
            'Error: ' + (error.error || error.message || 'Failed to record vote'),
            'danger');
        voteBtn.disabled = false;
        voteBtn.textContent = 'Submit Vote';
    });
};

function updateSinglePoll(pollId, updatedPoll) {
    const pollContainer = document.getElementById(`poll-options-${pollId}`);
    if (!pollContainer) return;

    const totalVotes = updatedPoll.total_votes || 0;

    updatedPoll.options.forEach((option, index) => {
        // Use option.id if available, otherwise use index + 1
        const optionId = option.id || (index + 1);
        const optionElement = document.getElementById(`poll-${pollId}-option-${optionId}`);
        if (optionElement) {
            const label = optionElement.nextElementSibling;
            const badge = label.querySelector('.badge');
            const progressBar = label.parentElement.nextElementSibling.querySelector('.progress-bar');

            if (badge) {
                badge.textContent = `${option.votes} votes (${option.percentage.toFixed(1)}%)`;
            }
            if (progressBar) {
                progressBar.style.width = `${option.percentage}%`;
                progressBar.setAttribute('aria-valuenow', option.percentage);
            }
        }
    });

    // Update total votes display
    const pollCard = document.getElementById(`poll-${pollId}`);
    const totalVotesElement = pollCard.querySelector('.text-muted');
    if (totalVotesElement) {
        totalVotesElement.textContent = `Total votes: ${totalVotes}`;
    }
}

// Utility function for escaping HTML
function escapeHtml(text) {
    if (!text) return '';
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, function(m) { return map[m]; });
}

// Utility function for showing messages
function showMessage(elementId, message, type = 'info') {
    const element = document.getElementById(elementId);
    if (!element) return;

    element.innerHTML = `
        <div class="alert alert-${type} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;

    // Auto-hide success messages
    if (type === 'success') {
        setTimeout(() => {
            element.innerHTML = '';
        }, 5000);
    }
}
});