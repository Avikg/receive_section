// WBSEDCL Tracking System - Client-side JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Auto-hide alerts after 5 seconds
    setTimeout(function() {
        const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
        alerts.forEach(function(alert) {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);

    // Confirm before forwarding
    const forwardForms = document.querySelectorAll('form[action*="forward"]');
    forwardForms.forEach(function(form) {
        form.addEventListener('submit', function(e) {
            if (!confirm('Are you sure you want to forward this document?')) {
                e.preventDefault();
            }
        });
    });

    // Date validation - ensure dates are not in future
    const dateInputs = document.querySelectorAll('input[type="date"]');
    dateInputs.forEach(function(input) {
        input.addEventListener('change', function() {
            const today = new Date().toISOString().split('T')[0];
            if (this.value > today) {
                alert('Date cannot be in the future');
                this.value = today;
            }
        });
    });

    // Table search functionality
    const searchInput = document.querySelector('#tableSearch');
    if (searchInput) {
        searchInput.addEventListener('keyup', function() {
            const filter = this.value.toLowerCase();
            const table = document.querySelector('.table tbody');
            const rows = table.querySelectorAll('tr');
            
            rows.forEach(function(row) {
                const text = row.textContent.toLowerCase();
                row.style.display = text.includes(filter) ? '' : 'none';
            });
        });
    }

    // Print functionality
    const printButtons = document.querySelectorAll('.btn-print');
    printButtons.forEach(function(btn) {
        btn.addEventListener('click', function() {
            window.print();
        });
    });

    // Form validation
    const forms = document.querySelectorAll('.needs-validation');
    forms.forEach(function(form) {
        form.addEventListener('submit', function(e) {
            if (!form.checkValidity()) {
                e.preventDefault();
                e.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });

    // Tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    ```javascript
    // WBSEDCL Tracking System - Client-side JavaScript

    document.addEventListener('DOMContentLoaded', function() {
        // Auto-hide alerts after 5 seconds
        setTimeout(function() {
            const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
            alerts.forEach(function(alert) {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            });
        }, 5000);

        // Confirm before forwarding
        const forwardForms = document.querySelectorAll('form[action*="forward"]');
        forwardForms.forEach(function(form) {
            form.addEventListener('submit', function(e) {
                if (!confirm('Are you sure you want to forward this document?')) {
                    e.preventDefault();
                }
            });
        });

        // Date validation - ensure dates are not in future
        const dateInputs = document.querySelectorAll('input[type="date"]');
        dateInputs.forEach(function(input) {
            input.addEventListener('change', function() {
                const today = new Date().toISOString().split('T')[0];
                if (this.value > today) {
                    alert('Date cannot be in the future');
                    this.value = today;
                }
            });
        });

        // Table search functionality
        const searchInput = document.querySelector('#tableSearch');
        if (searchInput) {
            searchInput.addEventListener('keyup', function() {
                const filter = this.value.toLowerCase();
                const table = document.querySelector('.table tbody');
                const rows = table.querySelectorAll('tr');
            
                rows.forEach(function(row) {
                    const text = row.textContent.toLowerCase();
                    row.style.display = text.includes(filter) ? '' : 'none';
                });
            });
        }

        // Print functionality
        const printButtons = document.querySelectorAll('.btn-print');
        printButtons.forEach(function(btn) {
            btn.addEventListener('click', function() {
                window.print();
            });
        });

        // Form validation
        const forms = document.querySelectorAll('.needs-validation');
        forms.forEach(function(form) {
            form.addEventListener('submit', function(e) {
                if (!form.checkValidity()) {
                    e.preventDefault();
                    e.stopPropagation();
                }
                form.classList.add('was-validated');
            });
        });

        // Tooltips
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });

        // Popovers
        const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
        popoverTriggerList.map(function (popoverTriggerEl) {
            return new bootstrap.Popover(popoverTriggerEl);
        });
    });

    // Format currency
    function formatCurrency(amount) {
        return new Intl.NumberFormat('en-IN', {
            style: 'currency',
            currency: 'INR'
        }).format(amount);
    }

    // Format date
    function formatDate(dateString) {
        const options = { year: 'numeric', month: 'short', day: 'numeric' };
        return new Date(dateString).toLocaleDateString('en-IN', options);
    }

    // Copy to clipboard
    function copyToClipboard(text) {
        navigator.clipboard.writeText(text).then(function() {
            alert('Copied to clipboard!');
        }, function() {
            alert('Failed to copy');
        });
    }

    // Export table to CSV
    function exportTableToCSV(filename) {
        const table = document.querySelector('.table');
        let csv = [];
        const rows = table.querySelectorAll('tr');
    
        rows.forEach(function(row) {
            const cols = row.querySelectorAll('td, th');
            const csvRow = [];
            cols.forEach(function(col) {
                csvRow.push('"' + col.innerText.replace(/"/g, '""') + '"');
            });
            csv.push(csvRow.join(','));
        });
    
        const csvFile = new Blob([csv.join('\n')], { type: 'text/csv' });
        const downloadLink = document.createElement('a');
        downloadLink.download = filename;
        downloadLink.href = window.URL.createObjectURL(csvFile);
        downloadLink.style.display = 'none';
        document.body.appendChild(downloadLink);
        downloadLink.click();
        document.body.removeChild(downloadLink);
    }
    ```