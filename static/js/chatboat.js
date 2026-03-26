// Chatbot JS

function toggleChat() {
  const win = document.getElementById('chatbot-window');
  win.classList.toggle('open');
  if (win.classList.contains('open')) {
    document.getElementById('chatbot-input').focus();
  }
}

function sendMessage() {
  const input = document.getElementById('chatbot-input');
  const msg   = input.value.trim();
  if (!msg) return;

  appendMessage(msg, 'user');
  input.value = '';

  // Typing indicator
  const typing = appendMessage('Thinking...', 'bot');

  fetch('/student/chat', {
    method:  'POST',
    headers: {'Content-Type': 'application/json'},
    body:    JSON.stringify({message: msg})
  })
  .then(r => r.json())
  .then(data => {
    typing.textContent = data.reply;
  })
  .catch(() => {
    typing.textContent = 'Sorry, something went wrong. Please try again.';
  });
}

function appendMessage(text, sender) {
  const messages = document.getElementById('chatbot-messages');
  const div = document.createElement('div');
  div.className = `chat-msg ${sender}`;
  div.textContent = text;
  messages.appendChild(div);
  messages.scrollTop = messages.scrollHeight;
  return div;
}