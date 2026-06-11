document.addEventListener('DOMContentLoaded', () => {
    const chatForm = document.getElementById('chat-form');
    const userInput = document.getElementById('user-input');
    const chatContainer = document.getElementById('chat-container');
    const contextContainer = document.getElementById('context-container');
    const contextEmptyState = document.getElementById('context-empty-state');
    const sendBtn = document.getElementById('send-btn');

    // Auto-resize textarea
    userInput.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
        if(this.value.trim() === '') {
            this.style.height = 'auto'; // reset
        }
        
        // Disable send button if empty
        if(this.value.trim() === '') {
            sendBtn.classList.add('opacity-50', 'cursor-not-allowed');
        } else {
            sendBtn.classList.remove('opacity-50', 'cursor-not-allowed');
        }
    });

    // Handle Enter to send (Shift+Enter for new line)
    userInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if(this.value.trim() !== '') {
                chatForm.dispatchEvent(new Event('submit'));
            }
        }
    });

    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const query = userInput.value.trim();
        if (!query) return;
        
        const useThink = document.getElementById('think-toggle').checked;

        // 1. Add user message to chat
        appendUserMessage(query);
        userInput.value = '';
        userInput.style.height = 'auto';
        sendBtn.classList.add('opacity-50', 'cursor-not-allowed');
        
        // 2. Add loading skeleton
        const loadingId = appendLoadingIndicator();
        
        // 3. Clear context panel and show loading state
        contextEmptyState.classList.add('hidden');
        const loadingText = useThink ? 'Đang phân tích (Think) và truy xuất cơ sở dữ liệu...' : 'Đang truy xuất cơ sở dữ liệu...';
        contextContainer.innerHTML = `
            <div class="text-center text-sm text-gray-400 mt-10 opacity-0 slide-in" style="animation-fill-mode: forwards;">
                <i class="fa-solid fa-circle-notch fa-spin mr-2 text-legal-highlight"></i> 
                ${loadingText}
            </div>`;

        // 4. Disable input
        userInput.disabled = true;
        sendBtn.disabled = true;

        try {
            // 5. Fetch API
            const response = await fetch('/api/query', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ query: query, use_think: useThink })
            });

            const data = await response.json();
            
            // Remove loading
            const loadingEl = document.getElementById(loadingId);
            if (loadingEl) loadingEl.remove();

            if (response.ok) {
                // Render Bot Message and sources
                appendBotMessage(data.response, data.metadata.context_blocks);
                
                // Render Context
                renderContext(data.metadata.context_blocks);
            } else {
                appendBotMessage("Xin lỗi, đã có lỗi xảy ra từ máy chủ: " + (data.error || "Unknown error"));
                contextContainer.innerHTML = '';
                contextEmptyState.classList.remove('hidden');
            }
            
        } catch (error) {
            const loadingEl = document.getElementById(loadingId);
            if (loadingEl) loadingEl.remove();
            appendBotMessage("Không thể kết nối đến máy chủ. Vui lòng kiểm tra lại mạng hoặc server.");
            contextContainer.innerHTML = '';
            contextEmptyState.classList.remove('hidden');
            console.error(error);
        } finally {
            // Re-enable input
            userInput.disabled = false;
            sendBtn.disabled = false;
            userInput.focus();
        }
    });

    function appendUserMessage(text) {
        const div = document.createElement('div');
        div.className = 'flex justify-end gap-4 opacity-0 slide-in mb-6';
        div.style.animationFillMode = 'forwards';
        
        div.innerHTML = `
            <div class="bg-legal-700/80 p-4 rounded-2xl rounded-tr-none max-w-[85%] shadow-md border border-legal-600/30">
                <p class="text-sm leading-relaxed">${text}</p>
            </div>
            <div class="w-8 h-8 rounded-full bg-gray-700 flex items-center justify-center text-gray-300 flex-shrink-0 mt-1">
                <i class="fa-solid fa-user text-sm"></i>
            </div>
        `;
        chatContainer.appendChild(div);
        scrollToBottom();
    }

    function appendBotMessage(text, blocks = null) {
        const div = document.createElement('div');
        div.className = 'flex gap-4 bot-message opacity-0 slide-in mb-6';
        div.style.animationFillMode = 'forwards';
        
        // Parse markdown text using marked.js
        const htmlContent = marked.parse(text);

        let sourcesHtml = '';
        if (blocks && blocks.length > 0) {
            sourcesHtml = `
                <div class="mt-4 pt-3 border-t border-legal-700/50">
                    <div class="text-xs text-gray-400 mb-2 font-semibold flex items-center gap-1">
                        <i class="fa-solid fa-book-bookmark"></i> Nguồn tham khảo:
                    </div>
                    <div class="space-y-2">
            `;
            blocks.forEach((block, idx) => {
                const textSnippet = block.text.length > 150 ? block.text.substring(0, 150) + '...' : block.text;
                sourcesHtml += `
                    <div class="text-xs bg-legal-900/50 p-2.5 rounded border border-legal-700/30 cursor-pointer hover:border-legal-highlight/50 transition-colors" title="${block.text}">
                        <span class="text-legal-highlight font-semibold mr-1">[Tài liệu ${idx + 1}]</span>
                        <span class="text-gray-300 italic">"${textSnippet}"</span>
                    </div>
                `;
            });
            sourcesHtml += `
                    </div>
                </div>
            `;
        }

        div.innerHTML = `
            <div class="w-8 h-8 rounded-full bg-legal-highlight/20 flex items-center justify-center text-legal-highlight flex-shrink-0 mt-1 shadow-sm">
                <i class="fa-solid fa-scale-balanced text-sm"></i>
            </div>
            <div class="bg-legal-800/60 p-4 rounded-2xl rounded-tl-none border border-legal-700/50 max-w-[85%] shadow-lg text-sm leading-relaxed w-full">
                <div class="markdown-body">${htmlContent}</div>
                ${sourcesHtml}
            </div>
        `;
        chatContainer.appendChild(div);
        scrollToBottom();
    }

    function appendLoadingIndicator() {
        const id = 'loading-' + Date.now();
        const div = document.createElement('div');
        div.id = id;
        div.className = 'flex gap-4 opacity-0 slide-in mb-6';
        div.style.animationFillMode = 'forwards';
        
        div.innerHTML = `
            <div class="w-8 h-8 rounded-full bg-legal-highlight/20 flex items-center justify-center text-legal-highlight flex-shrink-0 mt-1">
                <i class="fa-solid fa-robot text-sm"></i>
            </div>
            <div class="bg-legal-800/60 p-4 rounded-2xl rounded-tl-none border border-legal-700/50 max-w-[85%] shadow-lg space-y-3 w-64">
                <div class="h-2 skeleton-box rounded w-full"></div>
                <div class="h-2 skeleton-box rounded w-5/6"></div>
                <div class="h-2 skeleton-box rounded w-4/6"></div>
            </div>
        `;
        chatContainer.appendChild(div);
        scrollToBottom();
        return id;
    }

    function scrollToBottom() {
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    function renderContext(blocks) {
        contextContainer.innerHTML = '';
        
        if (!blocks || blocks.length === 0) {
            contextContainer.innerHTML = `
                <div class="flex flex-col items-center justify-center h-full text-gray-500 opacity-50">
                    <i class="fa-solid fa-folder-open text-4xl mb-3"></i>
                    <p class="text-sm">Không tìm thấy tài liệu liên quan đáp ứng tiêu chuẩn (Threshold).</p>
                </div>
            `;
            return;
        }

        blocks.forEach((block, index) => {
            const card = document.createElement('div');
            card.className = 'bg-legal-800/40 border border-legal-700/60 rounded-xl p-5 hover:border-legal-highlight/40 transition-colors opacity-0 slide-in group relative overflow-hidden';
            card.style.animationDelay = `${index * 0.1}s`;
            card.style.animationFillMode = 'forwards';
            
            // Format score
            const scorePercent = (block.score * 100).toFixed(1) + '%';
            
            card.innerHTML = `
                <div class="absolute top-0 left-0 w-1 h-full bg-legal-highlight/30 group-hover:bg-legal-highlight transition-colors"></div>
                <div class="flex justify-between items-center mb-3 pl-3">
                    <span class="text-xs font-semibold px-2 py-1 bg-legal-700 text-gray-300 rounded shadow-sm">Tài liệu [${index + 1}]</span>
                    <span class="text-xs font-mono px-2 py-1 bg-legal-highlight/10 text-legal-highlight rounded border border-legal-highlight/20" title="Reranker Confidence Score">
                        <i class="fa-solid fa-bullseye mr-1"></i> ${scorePercent}
                    </span>
                </div>
                <div class="text-sm text-gray-300 leading-relaxed pl-3 italic">
                    "${block.text}"
                </div>
            `;
            
            contextContainer.appendChild(card);
        });
    }
});
