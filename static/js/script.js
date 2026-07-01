/**
 * Library Management System - Client Side Javascript
 */

document.addEventListener('DOMContentLoaded', function () {
    // Sidebar toggle functionality
    const sidebarCollapse = document.getElementById('sidebarCollapse');
    const sidebar = document.getElementById('sidebar');
    if (sidebarCollapse && sidebar) {
        sidebarCollapse.addEventListener('click', function () {
            sidebar.classList.toggle('active');
        });
    }

    // Password Visibility Toggle
    const togglePassword = document.getElementById('togglePassword');
    const passwordInput = document.getElementById('password');
    if (togglePassword && passwordInput) {
        togglePassword.addEventListener('click', function () {
            // Toggle the type attribute
            const type = passwordInput.getAttribute('type') === 'password' ? 'text' : 'password';
            passwordInput.setAttribute('type', type);
            
            // Toggle the eye / eye-slash icon
            const icon = this.querySelector('i');
            if (icon) {
                if (type === 'text') {
                    icon.classList.remove('bi-eye');
                    icon.classList.add('bi-eye-slash');
                } else {
                    icon.classList.remove('bi-eye-slash');
                    icon.classList.add('bi-eye');
                }
            }
        });
    }

    // Auto-calculate Due Date (Issue Book Module)
    const issueDateInput = document.getElementById('issue_date');
    const dueDateInput = document.getElementById('due_date');
    if (issueDateInput && dueDateInput) {
        // Function to set due date +14 days from issue date
        const updateDueDate = () => {
            const issueDateVal = issueDateInput.value;
            if (issueDateVal) {
                const issueDate = new Date(issueDateVal);
                // Add 14 days
                issueDate.setDate(issueDate.getDate() + 14);
                
                // Format date as YYYY-MM-DD
                const yyyy = issueDate.getFullYear();
                let mm = issueDate.getMonth() + 1; // Months start at 0
                let dd = issueDate.getDate();
                
                if (mm < 10) mm = '0' + mm;
                if (dd < 10) dd = '0' + dd;
                
                dueDateInput.value = `${yyyy}-${mm}-${dd}`;
            }
        };

        // If issue date changes, update due date
        issueDateInput.addEventListener('change', updateDueDate);

        // Run initially if issue date is set but due date is not
        if (issueDateInput.value && !dueDateInput.value) {
            updateDueDate();
        }
    }

    // Confirm Delete Actions
    const deleteButtons = document.querySelectorAll('.confirm-delete');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function (e) {
            const message = this.getAttribute('data-confirm-message') || 'Are you sure you want to delete this item?';
            if (!confirm(message)) {
                e.preventDefault();
            }
        });
    });
});
