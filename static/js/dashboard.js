document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const whatsappNumberInput = document.getElementById('whatsapp-number');
    const verifyButton = document.getElementById('verify-button');
    const verificationMessage = document.getElementById('verification-message');
    const serviceCard = document.getElementById('service-card');
    const startServiceButton = document.getElementById('start-service-button');
    const stopServiceButton = document.getElementById('stop-service-button');
    const checkNowButton = document.getElementById('check-now-button');
    const serviceStatus = document.getElementById('service-status');
    const serviceAlert = document.getElementById('service-alert');
    const connectedWhatsapp = document.getElementById('connected-whatsapp');
    const lastChecked = document.getElementById('last-checked');
    const statusDot = document.getElementById('status-dot');
    
    // Initial status check
    checkServiceStatus();
    
    // Verify WhatsApp number
    verifyButton.addEventListener('click', function() {
        const whatsappNumber = whatsappNumberInput.value.trim();
        
        // Simple validation
        if (!whatsappNumber || !whatsappNumber.match(/^\+[0-9]{10,15}$/)) {
            showVerificationMessage('Please enter a valid WhatsApp number with country code (e.g., +91XXXXXXXXXX)', 'error');
            return;
        }
        
        // Disable button and show loading state
        verifyButton.disabled = true;
        verifyButton.textContent = 'Verifying...';
        
        // Send verification request
        fetch('/api/verify-whatsapp', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ whatsapp_number: whatsappNumber })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                showVerificationMessage('WhatsApp number verified successfully! You should receive a test message.', 'success');
                
                // Show service control card
                serviceCard.classList.remove('hidden');
                connectedWhatsapp.textContent = whatsappNumber;
                
                // Update status
                checkServiceStatus();
            } else {
                showVerificationMessage(`Error: ${data.message}`, 'error');
            }
        })
        .catch(error => {
            showVerificationMessage('Network error. Please try again.', 'error');
            console.error('Error:', error);
        })
        .finally(() => {
            // Re-enable button
            verifyButton.disabled = false;
            verifyButton.textContent = 'Verify Connection';
        });
    });
    
    // Start service
    startServiceButton.addEventListener('click', function() {
        startServiceButton.disabled = true;
        startServiceButton.textContent = 'Starting...';
        
        fetch('/api/start-service', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                updateServiceUI(true);
                serviceAlert.innerHTML = '<strong>Success!</strong> Your service is now active.';
                serviceAlert.className = 'alert alert-success';
            } else {
                serviceAlert.innerHTML = `<strong>Error:</strong> ${data.message}`;
                serviceAlert.className = 'alert alert-error';
            }
        })
        .catch(error => {
            serviceAlert.innerHTML = '<strong>Error:</strong> Network error. Please try again.';
            serviceAlert.className = 'alert alert-error';
            console.error('Error:', error);
        })
        .finally(() => {
            startServiceButton.disabled = false;
            startServiceButton.textContent = 'Start Service';
        });
    });
    
    // Stop service
    stopServiceButton.addEventListener('click', function() {
        stopServiceButton.disabled = true;
        stopServiceButton.textContent = 'Stopping...';
        
        fetch('/api/stop-service', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                updateServiceUI(false);
                serviceAlert.innerHTML = '<strong>Stopped:</strong> Your service has been stopped.';
                serviceAlert.className = 'alert alert-warning';
            } else {
                serviceAlert.innerHTML = `<strong>Error:</strong> ${data.message}`;
                serviceAlert.className = 'alert alert-error';
            }
        })
        .catch(error => {
            serviceAlert.innerHTML = '<strong>Error:</strong> Network error. Please try again.';
            serviceAlert.className = 'alert alert-error';
            console.error('Error:', error);
        })
        .finally(() => {
            stopServiceButton.disabled = false;
            stopServiceButton.textContent = 'Stop Service';
        });
    });
    
    // Check emails now
    checkNowButton.addEventListener('click', function() {
        checkNowButton.disabled = true;
        checkNowButton.textContent = 'Checking...';
        
        fetch('/api/check-now', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                lastChecked.textContent = data.last_check;
                serviceAlert.innerHTML = '<strong>Success:</strong> Checked for new emails.';
                serviceAlert.className = 'alert alert-success';
            } else {
                serviceAlert.innerHTML = `<strong>Error:</strong> ${data.message}`;
                serviceAlert.className = 'alert alert-error';
            }
        })
        .catch(error => {
            serviceAlert.innerHTML = '<strong>Error:</strong> Network error. Please try again.';
            serviceAlert.className = 'alert alert-error';
            console.error('Error:', error);
        })
        .finally(() => {
            checkNowButton.disabled = false;
            checkNowButton.textContent = 'Check Emails Now';
        });
    });
    
    // Helper functions
    function showVerificationMessage(message, type) {
        verificationMessage.textContent = message;
        verificationMessage.className = type;
        verificationMessage.classList.remove('hidden');
    }
    
    function updateServiceUI(isActive) {
        if (isActive) {
            serviceStatus.textContent = 'Active';
            statusDot.className = 'status-dot active';
            startServiceButton.classList.add('hidden');
            stopServiceButton.classList.remove('hidden');
            checkNowButton.classList.remove('hidden');
        } else {
            serviceStatus.textContent = 'Inactive';
            statusDot.className = 'status-dot inactive';
            startServiceButton.classList.remove('hidden');
            stopServiceButton.classList.add('hidden');
            checkNowButton.classList.add('hidden');
        }
    }
    
    function checkServiceStatus() {
        fetch('/api/status')
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    updateServiceUI(data.active);
                    
                    if (data.whatsapp_number) {
                        connectedWhatsapp.textContent = data.whatsapp_number;
                        serviceCard.classList.remove('hidden');
                    }
                    
                    if (data.last_check) {
                        lastChecked.textContent = data.last_check;
                    }
                }
            })
            .catch(error => {
                console.error('Error checking status:', error);
            });
    }
    
    // Periodically update status (every 30 seconds)
    setInterval(checkServiceStatus, 30000);
});