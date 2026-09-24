/**
 * Chef AI Assistant — Main Application Controller
 * Handles conversation state, real-time chat interactions,
 * markdown parsing, and UI reactivity.
 */

document.addEventListener('DOMContentLoaded', () => {
  // Enforce authentication
  if (!requireAuthentication()) return;

  // DOM Elements
  const sidebar = document.getElementById('sidebar');
  const mobileMenuToggle = document.getElementById('mobileMenuToggle');
  const conversationsList = document.getElementById('conversationsList');
  const btnNewChat = document.getElementById('btnNewChat');
  const btnSeedSample = document.getElementById('btnSeedSample');
  const btnLastRecipe = document.getElementById('btnLastRecipe');
  const btnLogout = document.getElementById('btnLogout');
  const currentChatTitle = document.getElementById('currentChatTitle');
  const chatMessages = document.getElementById('chatMessages');
  const welcomeScreen = document.getElementById('welcomeScreen');
  const loadingIndicator = document.getElementById('loadingIndicator');
  const chatInput = document.getElementById('chatInput');
  const btnSendMessage = document.getElementById('btnSendMessage');
  const btnAttachImage = document.getElementById('btnAttachImage');
  const imageFileInput = document.getElementById('imageFileInput');
  const imagePreviewChip = document.getElementById('imagePreviewChip');
  const imagePreviewThumb = document.getElementById('imagePreviewThumb');
  const imagePreviewName = document.getElementById('imagePreviewName');
  const btnRemoveImage = document.getElementById('btnRemoveImage');
  const btnSampleImage = document.getElementById('btnSampleImage');
  const userName = document.getElementById('userName');
  const userEmail = document.getElementById('userEmail');
  const userAvatar = document.getElementById('userAvatar');
  const toastContainer = document.getElementById('toastContainer');

  // App State
  let conversations = [];
  let currentConversationId = null;
  let isSending = false;

  // Attached image state (for the message about to be sent)
  let pendingImageBase64 = null;   // raw base64, no "data:" prefix
  let pendingImageMimeType = null;
  let pendingImageDataUrl = null;  // full data: URL, used for preview/rendering

  const API_ENDPOINTS = {
    me: '/auth/me',
    conversations: '/conversations',
    seedSamples: '/conversations/seed-samples',
    lastRecipe: '/conversations/recipes/last',
    conversation: id => `/conversations/${id}`,
    messages: id => `/conversations/${id}/messages`,
    recipeDecision: (convId, messageId) => `/conversations/${convId}/messages/${messageId}/recipe-decision`
  };

  // ==============================================================================
  // Initialization
  // ==============================================================================
  initUserProfile();
  loadConversations();
  setupEventListeners();

  function initUserProfile() {
    const user = getStoredUser();
    if (user) {
      userName.textContent = user.username || 'Chef';
      userEmail.textContent = user.email || '';
      userAvatar.textContent = (user.username ? user.username.charAt(0).toUpperCase() : '👨🍳');
    }

    // Optionally refresh user profile from backend
    authFetch(API_ENDPOINTS.me)
      .then(res => res.ok ? res.json() : null)
      .then(freshUser => {
        if (freshUser) {
          localStorage.setItem(USER_KEY, JSON.stringify(freshUser));
          userName.textContent = freshUser.username;
          userEmail.textContent = freshUser.email;
          userAvatar.textContent = freshUser.username.charAt(0).toUpperCase();
        }
      })
      .catch(() => {});
  }

  function setupEventListeners() {
    // Mobile sidebar toggle
    mobileMenuToggle.addEventListener('click', () => {
      sidebar.classList.toggle('open');
    });

    // Close mobile sidebar on outside click
    document.addEventListener('click', (e) => {
      if (window.innerWidth <= 860 && !sidebar.contains(e.target) && !mobileMenuToggle.contains(e.target)) {
        sidebar.classList.remove('open');
      }
    });

    // New conversation
    btnNewChat.addEventListener('click', () => {
      startNewConversation();
    });

    // Seed sample conversations
    btnSeedSample.addEventListener('click', () => {
      seedSampleConversations();
    });

    // Show the last saved recipe
    btnLastRecipe.addEventListener('click', () => {
      loadLastRecipe();
    });

    // Logout
    btnLogout.addEventListener('click', () => {
      logout();
    });

    // Send message on button click
    btnSendMessage.addEventListener('click', () => {
      handleSendMessage();
    });

    // Input keyboard handling: Enter to send, Shift+Enter for newline
    chatInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSendMessage();
      }
    });

    // Auto-expand textarea height
    chatInput.addEventListener('input', () => {
      chatInput.style.height = 'auto';
      chatInput.style.height = Math.min(chatInput.scrollHeight, 160) + 'px';
    });

    // Quick suggestion cards
    document.querySelectorAll('.suggestion-card').forEach(card => {
      card.addEventListener('click', () => {
        const prompt = card.getAttribute('data-prompt');
        if (prompt) {
          chatInput.value = prompt;
          handleSendMessage();
        }
      });
    });

    // Attach image button opens the hidden file input
    btnAttachImage.addEventListener('click', () => {
      imageFileInput.click();
    });

    imageFileInput.addEventListener('change', () => {
      const file = imageFileInput.files && imageFileInput.files[0];
      if (file) {
        attachImageFile(file);
      }
      imageFileInput.value = '';
    });

    btnRemoveImage.addEventListener('click', () => {
      clearAttachedImage();
    });

    // "Try an Image" suggestion card loads the bundled sample photo
    if (btnSampleImage) {
      btnSampleImage.addEventListener('click', async () => {
        try {
          const res = await fetch('assets/sample-ingredients.jpg');
          const blob = await res.blob();
          const file = new File([blob], 'sample-ingredients.jpg', { type: blob.type || 'image/jpeg' });
          attachImageFile(file);
          chatInput.value = 'What can I cook with the ingredients in this photo?';
          chatInput.focus();
        } catch (err) {
          showToast('Could not load the sample image.', 'error');
        }
      });
    }
  }

  // ==============================================================================
  // Image Attachment Helpers
  // ==============================================================================

  function attachImageFile(file) {
    if (!file.type.startsWith('image/')) {
      showToast('Please select an image file.', 'error');
      return;
    }
    // Keep uploads reasonable in size (5 MB) since images are stored as base64.
    if (file.size > 5 * 1024 * 1024) {
      showToast('Image is too large. Please choose one under 5 MB.', 'error');
      return;
    }

    const reader = new FileReader();
    reader.onload = () => {
      const dataUrl = reader.result; // e.g. "data:image/jpeg;base64,AAAA..."
      const [meta, base64] = dataUrl.split(',');
      const mimeMatch = meta.match(/data:(.*);base64/);

      pendingImageBase64 = base64;
      pendingImageMimeType = mimeMatch ? mimeMatch[1] : (file.type || 'image/jpeg');
      pendingImageDataUrl = dataUrl;

      imagePreviewThumb.src = dataUrl;
      imagePreviewName.textContent = file.name || 'image';
      imagePreviewChip.style.display = 'flex';
    };
    reader.onerror = () => {
      showToast('Could not read that image file.', 'error');
    };
    reader.readAsDataURL(file);
  }

  function clearAttachedImage() {
    pendingImageBase64 = null;
    pendingImageMimeType = null;
    pendingImageDataUrl = null;
    imagePreviewThumb.src = '';
    imagePreviewChip.style.display = 'none';
  }

  // ==============================================================================
  // Conversation Management
  // ==============================================================================

  async function loadConversations() {
    try {
      const res = await authFetch(API_ENDPOINTS.conversations);
      if (!res.ok) throw new Error('Failed to load conversations');
      conversations = await res.json();
      renderConversationsList();

      // Automatically select the most recent conversation if none is selected
      if (conversations.length > 0 && !currentConversationId) {
        await selectConversation(conversations[0].id);
      } else if (conversations.length === 0) {
        showWelcomeScreen();
      }
    } catch (err) {
      showToast(err.message, 'error');
    }
  }

  function renderConversationsList() {
    conversationsList.innerHTML = '';

    if (conversations.length === 0) {
      conversationsList.innerHTML = `
        <div style="padding: 1rem 0.5rem; text-align: center; color: #64748b; font-size: 0.85rem;">
          No conversations yet.<br>Click "+ New Conversation" to begin!
        </div>
      `;
      return;
    }

    conversations.forEach(conv => {
      const item = document.createElement('div');
      item.className = `conversation-item ${conv.id === currentConversationId ? 'active' : ''}`;
      item.innerHTML = `
        <div class="conversation-info" title="${escapeHtml(conv.title)}">
          <span style="font-size: 1.1rem;">💬</span>
          <span class="title">${escapeHtml(conv.title)}</span>
        </div>
        <div class="conversation-actions">
          <button class="btn-delete-conv" title="Delete conversation" data-id="${conv.id}">
            🗑️
          </button>
        </div>
      `;

      item.addEventListener('click', (e) => {
        if (e.target.closest('.btn-delete-conv')) return;
        selectConversation(conv.id);
        if (window.innerWidth <= 860) {
          sidebar.classList.remove('open');
        }
      });

      const delBtn = item.querySelector('.btn-delete-conv');
      delBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        deleteConversation(conv.id);
      });

      conversationsList.appendChild(item);
    });
  }

  async function selectConversation(convId) {
    if (currentConversationId === convId && chatMessages.children.length > 1) return;
    currentConversationId = convId;
    renderConversationsList();

    try {
      const res = await authFetch(API_ENDPOINTS.conversation(convId));
      if (!res.ok) {
        if (res.status === 404) {
          throw new Error('Conversation not found or access denied.');
        }
        throw new Error('Failed to load conversation details.');
      }

      const conversation = await res.json();
      currentChatTitle.textContent = conversation.title;

      // Render messages
      renderMessages(conversation.messages || []);
    } catch (err) {
      showToast(err.message, 'error');
      startNewConversation();
    }
  }

  function startNewConversation() {
    currentConversationId = null;
    currentChatTitle.textContent = 'New Conversation';
    renderConversationsList();
    showWelcomeScreen();
    chatInput.focus();
  }

  async function deleteConversation(convId) {
    if (!confirm('Are you sure you want to delete this conversation?')) return;

    try {
      const res = await authFetch(API_ENDPOINTS.conversation(convId), { method: 'DELETE' });
      if (!res.ok) throw new Error('Failed to delete conversation');

      showToast('Conversation deleted', 'success');
      conversations = conversations.filter(c => c.id !== convId);

      if (currentConversationId === convId) {
        if (conversations.length > 0) {
          selectConversation(conversations[0].id);
        } else {
          startNewConversation();
        }
      } else {
        renderConversationsList();
      }
    } catch (err) {
      showToast(err.message, 'error');
    }
  }

  async function seedSampleConversations() {
    try {
      showToast('Loading sample conversations...', 'info');
      const res = await authFetch(API_ENDPOINTS.seedSamples, { method: 'POST' });
      if (!res.ok) throw new Error('Could not load sample conversations.');
      
      const newConvos = await res.json();
      showToast('Sample conversations loaded! 🍝🥗🍰', 'success');
      await loadConversations();
      if (newConvos.length > 0) {
        selectConversation(newConvos[0].id);
      }
    } catch (err) {
      showToast(err.message, 'error');
    }
  }

  async function loadLastRecipe() {
    try {
      const res = await authFetch(API_ENDPOINTS.lastRecipe);
      if (!res.ok) {
        if (res.status === 404) {
          showToast('No saved recipe found yet.', 'info');
          return;
        }
        throw new Error('Could not load the last recipe.');
      }

      const recipe = await res.json();
      if (!recipe || !recipe.content) {
        throw new Error('The last recipe is empty.');
      }

      if (!currentConversationId) {
        const newConvoRes = await authFetch(API_ENDPOINTS.conversations, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ title: recipe.title || 'Last Recipe' })
        });
        if (!newConvoRes.ok) throw new Error('Could not start a conversation for the recipe.');
        const newConvo = await newConvoRes.json();
        currentConversationId = newConvo.id;
        conversations.unshift(newConvo);
        renderConversationsList();
      }

      currentChatTitle.textContent = recipe.title || 'Last Recipe';
      chatMessages.innerHTML = '';
      appendMessageToUI('assistant', recipe.content, true);
      showToast('Loaded your latest recipe.', 'success');
    } catch (err) {
      showToast(err.message, 'error');
    }
  }

  // ==============================================================================
  // Message Rendering & Flow
  // ==============================================================================

  function showWelcomeScreen() {
    chatMessages.innerHTML = '';
    chatMessages.appendChild(welcomeScreen);
    welcomeScreen.style.display = 'block';
  }

  function renderMessages(messages) {
    chatMessages.innerHTML = '';
    if (messages.length === 0) {
      showWelcomeScreen();
      return;
    }

    messages.forEach(msg => {
      const imageDataUrl = msg.image_base64
        ? `data:${msg.image_mime_type || 'image/jpeg'};base64,${msg.image_base64}`
        : null;
      appendMessageToUI(msg.role, msg.content, false, imageDataUrl);
    });
    scrollToBottom();
  }

  function appendMessageToUI(role, content, shouldScroll = true, imageDataUrl = null) {
    // Hide welcome screen on first message
    if (welcomeScreen.parentNode === chatMessages) {
      welcomeScreen.style.display = 'none';
      chatMessages.removeChild(welcomeScreen);
    }

    const row = document.createElement('div');
    row.className = `message-row ${role}`;

    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = role === 'user' ? (userName.textContent.charAt(0).toUpperCase() || 'U') : '👨🍳';

    const contentBox = document.createElement('div');
    contentBox.className = 'message-content';

    if (imageDataUrl) {
      const img = document.createElement('img');
      img.className = 'message-image';
      img.src = imageDataUrl;
      img.alt = 'Attached image';
      contentBox.appendChild(img);
    }

    const textEl = document.createElement('div');
    if (role === 'assistant') {
      textEl.innerHTML = renderMarkdown(content);
    } else {
      textEl.textContent = content;
    }
    contentBox.appendChild(textEl);

    row.appendChild(avatar);
    row.appendChild(contentBox);
    chatMessages.appendChild(row);

    if (shouldScroll) {
      scrollToBottom();
    }

    return contentBox;
  }

  // ==============================================================================
  // Human-in-the-Loop: Recipe Save Approval
  // ==============================================================================

  function appendRecipeApprovalPrompt(conversationId, messageId, contentBox) {
    const box = document.createElement('div');
    box.className = 'recipe-approval-box';

    const label = document.createElement('div');
    label.className = 'recipe-approval-label';
    label.textContent = '💾 Save this recipe to your recipe box?';
    box.appendChild(label);

    const actions = document.createElement('div');
    actions.className = 'recipe-approval-actions';

    const approveBtn = document.createElement('button');
    approveBtn.className = 'recipe-approval-btn approve';
    approveBtn.textContent = '✅ Approve';

    const rejectBtn = document.createElement('button');
    rejectBtn.className = 'recipe-approval-btn reject';
    rejectBtn.textContent = '❌ Reject';

    let deciding = false;
    async function sendDecision(approve) {
      if (deciding) return;
      deciding = true;
      approveBtn.disabled = true;
      rejectBtn.disabled = true;

      try {
        const res = await authFetch(API_ENDPOINTS.recipeDecision(conversationId, messageId), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ approve })
        });
        if (!res.ok) {
          const errorData = await res.json().catch(() => ({}));
          throw new Error(errorData.detail || 'Could not record your decision.');
        }
        const data = await res.json();

        label.textContent = data.saved
          ? '✅ Recipe saved to your recipe box.'
          : '❌ Recipe was not saved.';
        actions.remove();
        showToast(data.message || (data.saved ? 'Recipe saved!' : 'Recipe rejected.'), data.saved ? 'success' : 'info');
      } catch (err) {
        showToast(err.message, 'error');
        approveBtn.disabled = false;
        rejectBtn.disabled = false;
        deciding = false;
      }
    }

    approveBtn.addEventListener('click', () => sendDecision(true));
    rejectBtn.addEventListener('click', () => sendDecision(false));

    actions.appendChild(approveBtn);
    actions.appendChild(rejectBtn);
    box.appendChild(actions);

    contentBox.appendChild(box);
    scrollToBottom();
  }

  async function handleSendMessage() {
    const text = chatInput.value.trim();
    const hasImage = !!pendingImageBase64;
    if ((!text && !hasImage) || isSending) return;

    // Snapshot the attached image before clearing the input area
    const imageBase64ToSend = pendingImageBase64;
    const imageMimeTypeToSend = pendingImageMimeType;
    const imageDataUrlToSend = pendingImageDataUrl;

    // Reset input
    chatInput.value = '';
    chatInput.style.height = 'auto';
    clearAttachedImage();

    // 1. If no conversation is active, create one first
    if (!currentConversationId) {
      try {
        const createRes = await authFetch(API_ENDPOINTS.conversations, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ title: 'New Conversation' })
        });
        if (!createRes.ok) throw new Error('Could not start conversation');
        const newConvo = await createRes.json();
        currentConversationId = newConvo.id;
        conversations.unshift(newConvo);
        renderConversationsList();
      } catch (err) {
        showToast(err.message, 'error');
        return;
      }
    }

    // 2. Append user message to UI immediately
    appendMessageToUI('user', text || '🖼️ (Image attached)', true, imageDataUrlToSend);

    // 3. Set loading state
    setLoading(true);

    try {
      const payload = { content: text };
      if (imageBase64ToSend) {
        payload.image_base64 = imageBase64ToSend;
        payload.image_mime_type = imageMimeTypeToSend;
      }

      const response = await authFetch(API_ENDPOINTS.messages(currentConversationId), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        if (response.status === 404) {
          throw new Error('Conversation not found.');
        }
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Sorry, Chef AI is temporarily unavailable. Please try again.');
      }

      const data = await response.json();

      // 4. Render assistant response
      const assistantContentBox = appendMessageToUI('assistant', data.assistant_message.content, true);

      // 4b. Human-in-the-Loop: if this reply looks like a recipe, ask the
      // user to Approve/Reject saving it to the SQLite database.
      if (data.recipe_pending) {
        appendRecipeApprovalPrompt(currentConversationId, data.assistant_message.id, assistantContentBox);
      }

      // 5. Refresh conversations to show updated title and timestamp
      const refreshedResponse = await authFetch(API_ENDPOINTS.conversation(currentConversationId));
      if (!refreshedResponse.ok) {
        throw new Error('Message was sent, but the conversation could not be refreshed.');
      }
      const refreshedConvo = await refreshedResponse.json();
      if (refreshedConvo) {
        currentChatTitle.textContent = refreshedConvo.title;
        const idx = conversations.findIndex(c => c.id === currentConversationId);
        if (idx !== -1) {
          conversations[idx].title = refreshedConvo.title;
          conversations[idx].updated_at = refreshedConvo.updated_at;
          // Move to top
          const item = conversations.splice(idx, 1)[0];
          conversations.unshift(item);
          renderConversationsList();
        }
      }
    } catch (err) {
      showToast(err.message, 'error');
      appendMessageToUI('assistant', `⚠️ **Error:** ${err.message}`, true);
    } finally {
      setLoading(false);
      chatInput.focus();
    }
  }

  function setLoading(loading) {
    isSending = loading;
    btnSendMessage.disabled = loading;
    chatInput.disabled = loading;

    if (loading) {
      loadingIndicator.classList.add('active');
      chatMessages.appendChild(loadingIndicator);
      scrollToBottom();
    } else {
      loadingIndicator.classList.remove('active');
    }
  }

  function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  // ==============================================================================
  // Lightweight Custom Markdown Renderer for Recipes
  // ==============================================================================

  function renderMarkdown(text) {
    if (!text) return '';

    // Escape HTML first to prevent XSS
    let html = escapeHtml(text);

    // Headers
    html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
    html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
    html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');

    // Bold & Italic
    html = html.replace(/\*\*\*(.*?)\*\*\*/gim, '<strong><em>$1</em></strong>');
    html = html.replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>');
    html = html.replace(/\*(.*?)\*/gim, '<em>$1</em>');

    // Blockquotes (Chef's Tips)
    html = html.replace(/^\> (.*$)/gim, '<blockquote>$1</blockquote>');

    // Horizontal rules
    html = html.replace(/^---$/gim, '<hr>');

    // Numbered lists: 1. Step text
    html = html.replace(/^\s*(\d+)\.\s+(.*)$/gim, '<li><strong>Step $1:</strong> $2</li>');

    // Bullet lists: - item or * item
    html = html.replace(/^\s*[-*]\s+(.*)$/gim, '<li>$1</li>');

    // Group adjacent <li> into <ol> or <ul>
    html = html.replace(/(<li>.*<\/li>\s*)+/gim, (match) => {
      if (match.includes('Step')) {
        return `<ol>${match}</ol>`;
      }
      return `<ul>${match}</ul>`;
    });

    // Paragraphs and line breaks
    html = html.replace(/\n\n/g, '</p><p>');
    html = html.replace(/\n/g, '<br>');

    return `<div class="rendered-markdown">${html}</div>`;
  }

  function escapeHtml(str) {
    if (!str) return '';
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    const icon = type === 'error' ? '❌' : (type === 'success' ? '✅' : 'ℹ️');
    toast.innerHTML = `<span>${icon}</span> <span>${escapeHtml(message)}</span>`;
    toastContainer.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transition = 'opacity 0.4s ease';
      setTimeout(() => toast.remove(), 400);
    }, 4000);
  }
});
