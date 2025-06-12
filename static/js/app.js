/**
 * IezyPay - Main JavaScript
 * Handles all client-side functionality for the IezyPay application
 */

// Constants
const REFRESH_INTERVAL = 10000; // 10 seconds
let refreshTimer;

// Document ready function
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Setup AJAX request headers
    setupAjaxHeaders();
    
    // Initialize transaction refresh if on dashboard
    if (document.getElementById('transaction-list')) {
        startTransactionRefresh();
        setupRefreshButton();
    }
    
    // Initialize money transfer forms
    setupMoneyTransferForms();
});

/**
 * Sets up CSRF token and other headers for AJAX requests
 */
function setupAjaxHeaders() {
    // Add CSRF token to all AJAX requests if available
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    if (csrfToken) {
        $.ajaxSetup({
            beforeSend: function(xhr, settings) {
                if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type)) {
                    xhr.setRequestHeader("X-CSRFToken", csrfToken);
                }
                xhr.setRequestHeader("X-Requested-With", "XMLHttpRequest");
            }
        });
    } else {
        // If no CSRF token, at least set the XMLHttpRequest header
        $.ajaxSetup({
            beforeSend: function(xhr) {
                xhr.setRequestHeader("X-Requested-With", "XMLHttpRequest");
            }
        });
    }
}

/**
 * Sets up the manual refresh button with animation
 */
function setupRefreshButton() {
    const refreshBtn = document.getElementById('refresh-transactions');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', function() {
            const icon = this.querySelector('i');
            icon.classList.add('fa-spin');
            
            fetchLatestTransactions().then(() => {
                // Stop spinning after a short delay
                setTimeout(() => {
                    icon.classList.remove('fa-spin');
                }, 500);
            });
        });
    }
}

/**
 * Starts the automatic transaction refresh timer
 */
function startTransactionRefresh() {
    // Clear any existing timer
    if (refreshTimer) {
        clearInterval(refreshTimer);
    }
    
    // Initial fetch
    fetchLatestTransactions();
    
    // Set up interval for refreshing
    refreshTimer = setInterval(fetchLatestTransactions, REFRESH_INTERVAL);
}

/**
 * Fetches the latest transactions and updates the UI
 */
function fetchLatestTransactions() {
    return new Promise((resolve, reject) => {
        $.ajax({
            url: '/get-latest-transactions',
            type: 'GET',
            dataType: 'json',
            success: function(data) {
                if (data.success) {
                    updateTransactionsList(data.transactions);
                    updateBalanceDisplay(data.balance);
                    resolve();
                } else {
                    console.error('Error fetching transactions:', data.message);
                    reject(new Error(data.message));
                }
            },
            error: function(xhr, status, error) {
                console.error('AJAX error:', error);
                reject(error);
            }
        });
    });
}

/**
 * Updates the transactions list in the UI
 */
function updateTransactionsList(transactions) {
    const transactionList = document.getElementById('transaction-list');
    if (!transactionList) return;
    
    // Clear current transactions
    transactionList.innerHTML = '';
    
    if (transactions.length === 0) {
        transactionList.innerHTML = '<div class="text-center p-4 text-muted">No transactions found</div>';
        return;
    }
    
    // Add each transaction
    transactions.forEach(transaction => {
        const transactionItem = document.createElement('div');
        transactionItem.className = 'transaction-item p-3 border-bottom';
        
        const isCredit = transaction.transaction_type === 'credit';
        const amountClass = isCredit ? 'text-success' : 'text-danger';
        const amountPrefix = isCredit ? '+' : '-';
        
        transactionItem.innerHTML = `
            <div class="d-flex justify-content-between align-items-center">
                <div>
                    <div class="fw-bold">${transaction.description}</div>
                    <div class="text-muted small">
                        ${transaction.recipient ? `<span class="badge bg-light text-dark me-1">
                            <i class="fas fa-user me-1"></i>${transaction.recipient}
                        </span>` : ''}
                        <i class="far fa-clock me-1"></i>${transaction.timestamp}
                    </div>
                </div>
                <div class="h5 mb-0 ${amountClass}">${amountPrefix}₹${transaction.amount.toFixed(2)}</div>
            </div>
        `;
        
        transactionList.appendChild(transactionItem);
    });
}

/**
 * Updates the balance display in the UI
 */
function updateBalanceDisplay(balance) {
    const balanceElement = document.getElementById('user-balance');
    if (balanceElement) {
        balanceElement.textContent = `₹${balance.toFixed(2)}`;
    }
}

/**
 * Sets up the money transfer forms with AJAX submission
 */
function setupMoneyTransferForms() {
    // Phone transfer form
    const phoneTransferForm = document.getElementById('phone-transfer-form');
    if (phoneTransferForm) {
        phoneTransferForm.addEventListener('submit', function(e) {
            e.preventDefault();
            submitTransferForm(this, '/send-money/phone');
        });
    }
    
    // QR transfer form
    const qrTransferForm = document.getElementById('qr-transfer-form');
    if (qrTransferForm) {
        qrTransferForm.addEventListener('submit', function(e) {
            e.preventDefault();
            submitTransferForm(this, '/send-money/qr');
        });
    }
}

/**
 * Submits a transfer form via AJAX
 */
function submitTransferForm(form, endpoint) {
    const submitBtn = form.querySelector('button[type="submit"]');
    const originalBtnText = submitBtn.innerHTML;
    
    // Show loading state
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fas fa-circle-notch fa-spin"></i> Processing...';
    
    // Clear previous alerts
    const alertContainer = document.getElementById('alert-container');
    if (alertContainer) {
        alertContainer.innerHTML = '';
    }
    
    $.ajax({
        url: endpoint,
        type: 'POST',
        data: new FormData(form),
        processData: false,
        contentType: false,
        success: function(response) {
            if (response.success) {
                // Show success message
                showAlert('success', response.message);
                
                // Update balance if available
                if (response.new_balance !== undefined) {
                    updateBalanceDisplay(response.new_balance);
                }
                
                // Reset form
                form.reset();
                
                // Redirect after delay if not AJAX
                setTimeout(() => {
                    window.location.href = '/dashboard?transaction_success=true&message=' + encodeURIComponent(response.message);
                }, 1500);
            } else {
                // Show error message
                showAlert('danger', response.message);
            }
        },
        error: function(xhr, status, error) {
            showAlert('danger', 'An error occurred while processing your request. Please try again.');
            console.error('AJAX error:', error);
        },
        complete: function() {
            // Restore button state
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalBtnText;
        }
    });
}

/**
 * Shows an alert message
 */
function showAlert(type, message) {
    const alertContainer = document.getElementById('alert-container');
    if (!alertContainer) return;
    
    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show`;
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    alertContainer.appendChild(alert);
    
    // Auto dismiss after 5 seconds
    setTimeout(() => {
        const bsAlert = new bootstrap.Alert(alert);
        bsAlert.close();
    }, 5000);
} 