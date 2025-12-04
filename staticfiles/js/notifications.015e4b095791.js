// ============================================
// NOTIFICATIONS SYSTEM
// Real-time polling + Sound + Web Notifications
// ============================================

let lastNotificationCount = 0;
let notificationSound = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    // Request notification permission
    if ('Notification' in window && Notification.permission === 'default') {
        Notification.requestPermission();
    }
    
    // Initialize sound
    notificationSound = document.getElementById('notificationSound');
    
    // Start polling
    startNotificationPolling();
    
    // Load initial notifications
    loadNotifications();
});

// Start polling every 15 seconds
function startNotificationPolling() {
    // Initial check
    checkNewNotifications();
    
    // Poll every 15 seconds
    setInterval(checkNewNotifications, 15000);
}

// Check for new notifications
async function checkNewNotifications() {
    try {
        const response = await fetch('/notifications/api/unread-count/');
        const data = await response.json();
        
        const count = data.count;
        const badge = document.getElementById('notificationCount');
        
        if (badge) {
            if (count > 0) {
                badge.textContent = count;
                badge.style.display = 'block';
            } else {
                badge.style.display = 'none';
            }
        }
        
        // If count increased, play sound and show notification
        if (count > lastNotificationCount) {
            playNotificationSound();
            loadRecentNotifications();
        }
        
        lastNotificationCount = count;
        
    } catch (error) {
        console.error('Notification check failed:', error);
    }
}

// Load recent notifications for dropdown
async function loadRecentNotifications() {
    try {
        const response = await fetch('/notifications/api/recent/');
        const data = await response.json();
        
        const list = document.getElementById('notificationsList');
        if (!list) return;
        
        if (data.notifications && data.notifications.length > 0) {
            list.innerHTML = '';
            
            data.notifications.forEach(notif => {
                const item = createNotificationItem(notif);
                list.appendChild(item);
                
                // Show browser notification for first one
                if (data.notifications[0].id === notif.id) {
                    showBrowserNotification(notif);
                }
            });
        } else {
            list.innerHTML = '<p class="no-notifications">Yangi bildirishnomalar yo\'q</p>';
        }
        
    } catch (error) {
        console.error('Failed to load notifications:', error);
    }
}

// Load all notifications (called when dropdown opens)
function loadNotifications() {
    loadRecentNotifications();
}

// Create notification item HTML
function createNotificationItem(notif) {
    const div = document.createElement('div');
    div.className = 'notification-item';
    div.onclick = function() {
        markAsReadAndRedirect(notif.id, notif.url);
    };
    
    div.innerHTML = `
        <div class="notification-content">
            <div class="notification-title">${escapeHtml(notif.title)}</div>
            <div class="notification-text">${escapeHtml(notif.text)}</div>
            <div class="notification-time">${notif.created_at}</div>
        </div>
    `;
    
    return div;
}

// Mark notification as read and redirect
function markAsReadAndRedirect(id, url) {
    fetch(`/notifications/${id}/read/`, {
        method: 'GET',
    }).then(() => {
        if (url) {
            window.location.href = url;
        }
    });
}

// Toggle notifications dropdown
function toggleNotifications() {
    const dropdown = document.getElementById('notificationsDropdown');
    if (dropdown) {
        dropdown.classList.toggle('active');
        
        if (dropdown.classList.contains('active')) {
            loadRecentNotifications();
        }
    }
}

// Close dropdown when clicking outside
document.addEventListener('click', function(event) {
    const bell = document.querySelector('.notifications-bell');
    const dropdown = document.getElementById('notificationsDropdown');
    
    if (bell && dropdown && !bell.contains(event.target)) {
        dropdown.classList.remove('active');
    }
});

// Play notification sound
function playNotificationSound() {
    if (notificationSound) {
        notificationSound.play().catch(err => {
            console.log('Sound play failed:', err);
        });
    }
}

// Show browser notification
function showBrowserNotification(notif) {
    if ('Notification' in window && Notification.permission === 'granted') {
        const notification = new Notification(notif.title, {
            body: notif.text,
            icon: '/static/images/logo.png',
            badge: '/static/images/logo.png',
            tag: 'iiv-notification-' + notif.id,
            requireInteraction: false,
        });
        
        notification.onclick = function() {
            window.focus();
            if (notif.url) {
                window.location.href = notif.url;
            }
            notification.close();
        };
        
        // Auto close after 5 seconds
        setTimeout(() => {
            notification.close();
        }, 5000);
    }
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Export functions for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        toggleNotifications,
        loadNotifications,
        checkNewNotifications,
    };
}