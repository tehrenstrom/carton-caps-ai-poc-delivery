const chatbox = document.getElementById('chatbox');
const userInput = document.getElementById('userInput');
const sendButton = document.getElementById('sendButton');
const userSelect = document.getElementById('userSelect');
const userSelectorArea = document.querySelector('.user-selector-area');

// Cache management for API calls
const apiCache = {
    data: {},
    timeouts: {},
    cacheDuration: 5 * 60 * 1000, 

    async get(endpoint) {
        const now = Date.now();
        if (this.data[endpoint] && this.timeouts[endpoint] > now) {
            return this.data[endpoint];
        }
        
        try {
            const response = await fetch(endpoint);
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            const data = await response.json();
            
            this.data[endpoint] = data;
            this.timeouts[endpoint] = now + this.cacheDuration;
            
            return data;
        } catch (error) {
            console.error(`Cache fetch error for ${endpoint}:`, error);
            if (this.data[endpoint]) return this.data[endpoint];
            throw error;
        }
    },

    clear(endpoint) {
        if (endpoint) {
            delete this.data[endpoint];
            delete this.timeouts[endpoint];
        } else {
            this.data = {};
            this.timeouts = {};
        }
    }
};

// FE add message function
function addMessage(message, sender) {
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message');
    const senderClass = sender === 'user' ? 'user-message' : 'bot-message';
    messageDiv.classList.add(senderClass);

    if (sender === 'bot' && message !== 'Thinking...') {
        messageDiv.classList.add('bot-message-with-icon');
    }

    if (sender === 'bot' && message === 'Thinking...') {
        messageDiv.classList.add('thinking');
        const dotsDiv = document.createElement('div');
        dotsDiv.className = 'thinking-dots';
        for (let i = 0; i < 3; i++) {
            const dot = document.createElement('span');
            dotsDiv.appendChild(dot);
        }
        messageDiv.appendChild(dotsDiv);
    } else {
        messageDiv.textContent = message;
    }

    chatbox.appendChild(messageDiv);
    chatbox.scrollTop = chatbox.scrollHeight;
    return messageDiv; 
}

// FE populate users dropdown
async function populateUsers() {
    try {
        const users = await apiCache.get('/users');
        
        userSelect.innerHTML = '';

        if (users.length === 0) {
            userSelect.innerHTML = '<option value="" disabled selected>No profiles found</option>';
            return;
        }

        const defaultOption = document.createElement('option');
        defaultOption.value = "";
        defaultOption.textContent = "Select a Profile";
        defaultOption.disabled = true;
        defaultOption.selected = true;
        userSelect.appendChild(defaultOption);

        users.forEach(user => {
            const option = document.createElement('option');
            option.value = user.id;
            option.textContent = user.name;
            userSelect.appendChild(option);
        });

    } catch (error) {
        console.error('Error fetching users:', error);
        userSelect.innerHTML = '<option value="" disabled selected>Error loading users</option>';
    }
}

// FE display initial bot messages
async function displayInitialMessages(userId) {
    const placeholder = chatbox.querySelector('.initial-placeholder');
    if (placeholder) {
        placeholder.remove();
    }
    chatbox.innerHTML = '';

    if (!userId) return;

    try {
        const users = await apiCache.get('/users');
        const userData = users.find(u => u.id === parseInt(userId));
        
        if (!userData) {
            addMessage("Error loading customer info. Please try selecting again.", 'bot');
            return;
        }

        const firstName = userData.name ? userData.name.split(' ')[0] : 'there';
        const schoolName = userData.school_name;

        let firstMessage = `Hi ${firstName}! I'm Capper, your personal Carton Caps assistant.`;
        if (schoolName) {
            firstMessage += ` Your purchases from us help to fund critical school programming efforts for ${schoolName}.`;
        } else {
            firstMessage += ` Your purchases from us help fund critical school programming efforts.`;
        }

        addMessage(firstMessage, 'bot');
        addMessage("Ask me a question, and I'll do my best to help you. I'm currently equipped to help you with the Carton Caps products, our referral program and FAQs.", 'bot');
        addMessage(
            "If there's anything I can't help you with, I'll direct you to someone who can.",
            'bot'
        );

    } catch (error) {
        console.error('Error displaying initial messages:', error);
        addMessage("Sorry, couldn't load initial messages. Please try again.", 'bot');
    }
}

// Global var for current conversation ID
let currentConversationId = null;

// FE send message
async function sendMessage() {
    const messageText = userInput.value.trim();
    const selectedUserId = userSelect.value;

    if (!messageText) {
        return; 
    }
    if (!selectedUserId) {
        console.warn("No user selected.");
        userSelect.focus();
        return;
    }

    const userId = parseInt(selectedUserId);

    addMessage(messageText, 'user');
    userInput.value = '';

    const thinkingMessageDiv = addMessage('Thinking...', 'bot');

    try {
        const response = await fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'accept': 'application/json'
            },
            body: JSON.stringify({
                user_id: userId,
                message: messageText,
                conversation_id: currentConversationId
            })
        });

        chatbox.removeChild(thinkingMessageDiv);

        if (!response.ok) {
            const errorData = await response.json();
            console.error('API Error:', errorData);
            addMessage(`Error: ${errorData.detail || response.statusText}`, 'bot');
            if (response.status === 404) {
                currentConversationId = null; 
            }
            return;
        }

        const data = await response.json();
        
        currentConversationId = data.conversation_id;
        
        addMessage(data.response, 'bot');

    } catch (error) {
        if (chatbox.contains(thinkingMessageDiv)) {
            chatbox.removeChild(thinkingMessageDiv);
        }
        console.error('Fetch Error:', error);
        addMessage('Sorry, I couldn\'t connect. Please check the console.', 'bot');
    }
}

// Initialize everything
document.addEventListener('DOMContentLoaded', () => {
    populateUsers();
});

// Event Listeners
sendButton.addEventListener('click', sendMessage);
userInput.addEventListener('keypress', (event) => {
    if (event.key === 'Enter') {
        sendMessage();
    }
});

userSelect.addEventListener('change', function(event) {
    const selectedUserId = event.target.value;
    currentConversationId = null;
    displayInitialMessages(selectedUserId);
}); 