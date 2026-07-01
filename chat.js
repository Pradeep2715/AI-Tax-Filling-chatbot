/* ============================================================
   TaxBot — AI-Powered Tax Filing Chatbot
   Complete Frontend Application
   ============================================================ */

// ======================== PARTICLE BACKGROUND ========================
class ParticleBackground {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        if (!this.canvas) return;
        this.ctx = this.canvas.getContext('2d');
        this.particles = [];
        this.mouseX = 0;
        this.mouseY = 0;
        this.animationId = null;
        this.resize();
        this.init();
        this.animate();
        window.addEventListener('resize', () => this.resize());
        window.addEventListener('mousemove', (e) => {
            this.mouseX = e.clientX;
            this.mouseY = e.clientY;
        });
    }

    resize() {
        this.canvas.width = window.innerWidth;
        this.canvas.height = window.innerHeight;
    }

    init() {
        this.particles = [];
        const count = Math.min(80, Math.floor(window.innerWidth / 15));
        for (let i = 0; i < count; i++) {
            this.particles.push({
                x: Math.random() * this.canvas.width,
                y: Math.random() * this.canvas.height,
                radius: Math.random() * 2 + 0.5,
                vx: (Math.random() - 0.5) * 0.5,
                vy: (Math.random() - 0.5) * 0.5,
                opacity: Math.random() * 0.5 + 0.2
            });
        }
    }

    animate() {
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        this.particles.forEach((p, i) => {
            // Mouse repulsion
            const dx = p.x - this.mouseX;
            const dy = p.y - this.mouseY;
            const mouseDist = Math.hypot(dx, dy);
            if (mouseDist < 150) {
                const force = (150 - mouseDist) / 150;
                p.vx += (dx / mouseDist) * force * 0.02;
                p.vy += (dy / mouseDist) * force * 0.02;
            }

            // Damping
            p.vx *= 0.999;
            p.vy *= 0.999;

            p.x += p.vx;
            p.y += p.vy;

            if (p.x < 0 || p.x > this.canvas.width) p.vx *= -1;
            if (p.y < 0 || p.y > this.canvas.height) p.vy *= -1;

            // Draw particle
            this.ctx.beginPath();
            this.ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
            this.ctx.fillStyle = `rgba(102, 126, 234, ${p.opacity})`;
            this.ctx.fill();

            // Draw connections
            for (let j = i + 1; j < this.particles.length; j++) {
                const p2 = this.particles[j];
                const dist = Math.hypot(p.x - p2.x, p.y - p2.y);
                if (dist < 120) {
                    this.ctx.beginPath();
                    this.ctx.moveTo(p.x, p.y);
                    this.ctx.lineTo(p2.x, p2.y);
                    this.ctx.strokeStyle = `rgba(102, 126, 234, ${0.15 * (1 - dist / 120)})`;
                    this.ctx.lineWidth = 0.5;
                    this.ctx.stroke();
                }
            }
        });
        this.animationId = requestAnimationFrame(() => this.animate());
    }
}

// ======================== TAXBOT APP ========================
class TaxBotApp {
    constructor() {
        this.isAuthenticated = false;
        this.userEmail = '';
        this.pendingOtpEmail = '';
        this.historyOpen = false;
        this.otpTimerInterval = null;
        this.isTyping = false;
        this.init();
    }

    async init() {
        new ParticleBackground('particles-canvas');
        this.bindEvents();
        await this.checkAuth();
    }

    // ======================== EVENT BINDING ========================
    bindEvents() {
        // Auth tab switching
        const tabLogin = document.getElementById('tab-login');
        const tabRegister = document.getElementById('tab-register');
        const switchToRegister = document.getElementById('switch-to-register');
        const switchToLogin = document.getElementById('switch-to-login');

        if (tabLogin) tabLogin.addEventListener('click', () => this.switchAuthTab('login'));
        if (tabRegister) tabRegister.addEventListener('click', () => this.switchAuthTab('register'));
        if (switchToRegister) switchToRegister.addEventListener('click', (e) => { e.preventDefault(); this.switchAuthTab('register'); });
        if (switchToLogin) switchToLogin.addEventListener('click', (e) => { e.preventDefault(); this.switchAuthTab('login'); });

        // Login form
        const loginForm = document.getElementById('login-form');
        if (loginForm) {
            loginForm.addEventListener('submit', (e) => {
                e.preventDefault();
                const email = document.getElementById('login-email').value.trim();
                const password = document.getElementById('login-password').value;
                this.handleLogin(email, password);
            });
        }

        // Register form
        const registerForm = document.getElementById('register-form');
        if (registerForm) {
            registerForm.addEventListener('submit', (e) => {
                e.preventDefault();
                const email = document.getElementById('register-email').value.trim();
                const password = document.getElementById('register-password').value;
                const confirmPassword = document.getElementById('register-confirm-password').value;
                this.handleRegister(email, password, confirmPassword);
            });
        }

        // Toggle password visibility
        document.querySelectorAll('.toggle-password').forEach(btn => {
            btn.addEventListener('click', () => {
                const target = document.getElementById(btn.dataset.target);
                if (target) {
                    const isPassword = target.type === 'password';
                    target.type = isPassword ? 'text' : 'password';
                    btn.textContent = isPassword ? '🙈' : '👁️';
                }
            });
        });

        // OTP input auto-focus
        const otpDigits = document.querySelectorAll('.otp-digit');
        otpDigits.forEach((input, index) => {
            input.addEventListener('input', (e) => {
                const val = e.target.value.replace(/[^0-9]/g, '');
                e.target.value = val;
                if (val && index < otpDigits.length - 1) {
                    otpDigits[index + 1].focus();
                }
                if (val) e.target.classList.add('filled');
                else e.target.classList.remove('filled');
            });
            input.addEventListener('keydown', (e) => {
                if (e.key === 'Backspace' && !e.target.value && index > 0) {
                    otpDigits[index - 1].focus();
                    otpDigits[index - 1].value = '';
                    otpDigits[index - 1].classList.remove('filled');
                }
            });
            input.addEventListener('paste', (e) => {
                e.preventDefault();
                const pasteData = (e.clipboardData || window.clipboardData).getData('text').replace(/[^0-9]/g, '').slice(0, 6);
                pasteData.split('').forEach((digit, i) => {
                    if (otpDigits[i]) {
                        otpDigits[i].value = digit;
                        otpDigits[i].classList.add('filled');
                    }
                });
                const nextIndex = Math.min(pasteData.length, otpDigits.length - 1);
                otpDigits[nextIndex].focus();
            });
        });

        // Verify OTP
        const verifyOtpBtn = document.getElementById('verify-otp-btn');
        if (verifyOtpBtn) verifyOtpBtn.addEventListener('click', () => this.handleVerifyOTP());

        // Resend OTP
        const resendOtpBtn = document.getElementById('resend-otp-btn');
        if (resendOtpBtn) {
            resendOtpBtn.addEventListener('click', () => {
                if (!resendOtpBtn.disabled) {
                    this.handleRegister(this.pendingOtpEmail, this._lastPassword, this._lastPassword);
                }
            });
        }

        // Chat input
        const chatInput = document.getElementById('chat-input');
        const sendBtn = document.getElementById('send-btn');

        if (chatInput) {
            chatInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage(chatInput.value);
                }
            });
        }

        if (sendBtn) sendBtn.addEventListener('click', () => {
            const input = document.getElementById('chat-input');
            if (input) this.sendMessage(input.value);
        });

        // Header actions
        const historyBtn = document.getElementById('history-btn');
        const newChatBtn = document.getElementById('new-chat-btn');
        const logoutBtn = document.getElementById('logout-btn');
        const closeSidebarBtn = document.getElementById('close-sidebar-btn');

        if (historyBtn) historyBtn.addEventListener('click', () => this.toggleHistory());
        if (newChatBtn) newChatBtn.addEventListener('click', () => this.startNewSession());
        if (logoutBtn) logoutBtn.addEventListener('click', () => this.handleLogout());
        if (closeSidebarBtn) closeSidebarBtn.addEventListener('click', () => this.toggleHistory());

        // Modal close
        const closeModalBtn = document.getElementById('close-modal-btn');
        const modalOverlay = document.getElementById('session-modal');

        if (closeModalBtn) closeModalBtn.addEventListener('click', () => this.closeModal());
        if (modalOverlay) {
            modalOverlay.addEventListener('click', (e) => {
                if (e.target === modalOverlay) this.closeModal();
            });
        }

        // Escape key handler
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeModal();
                if (this.historyOpen) this.toggleHistory();
            }
        });
    }

    // ======================== AUTH TAB SWITCHING ========================
    switchAuthTab(tab) {
        const loginForm = document.getElementById('login-form');
        const registerForm = document.getElementById('register-form');
        const otpSection = document.getElementById('otp-section');
        const tabLogin = document.getElementById('tab-login');
        const tabRegister = document.getElementById('tab-register');
        const indicator = document.querySelector('.tab-indicator');

        this.clearAuthMessage();

        if (tab === 'login') {
            loginForm.classList.remove('hidden');
            registerForm.classList.add('hidden');
            otpSection.classList.add('hidden');
            tabLogin.classList.add('active');
            tabLogin.setAttribute('aria-selected', 'true');
            tabRegister.classList.remove('active');
            tabRegister.setAttribute('aria-selected', 'false');
            indicator.classList.remove('right');
        } else {
            loginForm.classList.add('hidden');
            registerForm.classList.remove('hidden');
            otpSection.classList.add('hidden');
            tabRegister.classList.add('active');
            tabRegister.setAttribute('aria-selected', 'true');
            tabLogin.classList.remove('active');
            tabLogin.setAttribute('aria-selected', 'false');
            indicator.classList.add('right');
        }
    }

    // ======================== SCREEN MANAGEMENT ========================
    showScreen(screenId) {
        document.querySelectorAll('.screen').forEach(s => s.classList.add('hidden'));
        const screen = document.getElementById(screenId);
        if (screen) {
            screen.classList.remove('hidden');
            screen.classList.add('fade-in');
            setTimeout(() => screen.classList.remove('fade-in'), 500);
        }
    }

    // ======================== AUTH CHECK ========================
    async checkAuth() {
        try {
            const res = await fetch('/api/check-auth');
            const data = await res.json();
            if (data.authenticated) {
                this.isAuthenticated = true;
                this.userEmail = data.email;
                this.showAppScreen();
            } else {
                this.showScreen('auth-screen');
            }
        } catch (err) {
            this.showScreen('auth-screen');
        }
    }

    showAppScreen() {
        this.showScreen('app-screen');
        const emailDisplay = document.getElementById('user-email-display');
        if (emailDisplay && this.userEmail) {
            const part = this.userEmail.split('@')[0];
            const cleanName = part.replace(/[0-9_.-]+/g, ' ').trim().replace(/\b\w/g, c => c.toUpperCase());
            emailDisplay.textContent = cleanName || this.userEmail;
        }
    }

    // ======================== LOGIN ========================
    async handleLogin(email, password) {
        if (!email || !password) {
            this.showAuthMessage('Please fill in all fields.', 'error');
            return;
        }

        const btn = document.querySelector('#login-form .btn-submit');
        this.setButtonLoading(btn, true);

        try {
            const res = await fetch('/api/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password })
            });
            const data = await res.json();

            if (data.success) {
                this.isAuthenticated = true;
                this.userEmail = data.email || email;
                this.showAuthMessage('Login successful! Redirecting...', 'success');
                setTimeout(() => {
                    this.showAppScreen();
                    this.startNewSession();
                }, 600);
            } else {
                this.showAuthMessage(data.message || 'Login failed. Please try again.', 'error');
            }
        } catch (err) {
            this.showAuthMessage('Network error. Please check your connection.', 'error');
        } finally {
            this.setButtonLoading(btn, false);
        }
    }

    // ======================== REGISTER ========================
    async handleRegister(email, password, confirmPassword) {
        if (!email || !password || !confirmPassword) {
            this.showAuthMessage('Please fill in all fields.', 'error');
            return;
        }

        if (password !== confirmPassword) {
            this.showAuthMessage('Passwords do not match.', 'error');
            return;
        }

        if (password.length < 6) {
            this.showAuthMessage('Password must be at least 6 characters.', 'error');
            return;
        }

        const btn = document.querySelector('#register-form .btn-submit');
        this.setButtonLoading(btn, true);
        this._lastPassword = password;

        try {
            const res = await fetch('/api/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password })
            });
            const data = await res.json();

            if (data.success) {
                this.pendingOtpEmail = email;
                this.showOTPSection(email, data.otp);
                this.showAuthMessage('Registration successful! Please verify your email.', 'success');
            } else {
                this.showAuthMessage(data.message || 'Registration failed.', 'error');
            }
        } catch (err) {
            this.showAuthMessage('Network error. Please check your connection.', 'error');
        } finally {
            this.setButtonLoading(btn, false);
        }
    }

    // ======================== OTP ========================
    showOTPSection(email, otp) {
        const loginForm = document.getElementById('login-form');
        const registerForm = document.getElementById('register-form');
        const otpSection = document.getElementById('otp-section');
        const otpEmailDisplay = document.getElementById('otp-email-display');

        loginForm.classList.add('hidden');
        registerForm.classList.add('hidden');
        otpSection.classList.remove('hidden');

        if (otpEmailDisplay) otpEmailDisplay.textContent = email;

        // Clear OTP inputs
        document.querySelectorAll('.otp-digit').forEach(input => {
            input.value = '';
            input.classList.remove('filled');
        });

        // Focus first digit
        const firstDigit = document.querySelector('.otp-digit');
        if (firstDigit) setTimeout(() => firstDigit.focus(), 100);

        this.startOTPTimer(120);

        // If OTP is provided (for dev/testing), auto-fill
        if (otp) {
            const digits = String(otp).split('');
            document.querySelectorAll('.otp-digit').forEach((input, i) => {
                if (digits[i]) {
                    input.value = digits[i];
                    input.classList.add('filled');
                }
            });
        }
    }

    async handleVerifyOTP() {
        const digits = Array.from(document.querySelectorAll('.otp-digit')).map(i => i.value).join('');

        if (digits.length !== 6) {
            this.showAuthMessage('Please enter all 6 digits.', 'error');
            return;
        }

        const btn = document.getElementById('verify-otp-btn');
        this.setButtonLoading(btn, true);

        try {
            const res = await fetch('/api/verify-otp', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email: this.pendingOtpEmail, otp: digits })
            });
            const data = await res.json();

            if (data.success) {
                this.isAuthenticated = true;
                this.userEmail = this.pendingOtpEmail;
                this.showAuthMessage('Email verified! Redirecting...', 'success');
                clearInterval(this.otpTimerInterval);
                setTimeout(() => {
                    this.showAppScreen();
                    this.startNewSession();
                }, 600);
            } else {
                this.showAuthMessage(data.message || 'Invalid OTP. Please try again.', 'error');
            }
        } catch (err) {
            this.showAuthMessage('Network error. Please check your connection.', 'error');
        } finally {
            this.setButtonLoading(btn, false);
        }
    }

    startOTPTimer(seconds) {
        clearInterval(this.otpTimerInterval);
        const timerEl = document.getElementById('otp-timer');
        const resendBtn = document.getElementById('resend-otp-btn');
        let remaining = seconds;

        if (resendBtn) resendBtn.disabled = true;

        const updateTimer = () => {
            const mins = Math.floor(remaining / 60);
            const secs = remaining % 60;
            if (timerEl) timerEl.textContent = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;

            if (remaining <= 0) {
                clearInterval(this.otpTimerInterval);
                if (resendBtn) resendBtn.disabled = false;
                if (timerEl) timerEl.textContent = '00:00';
            }
            remaining--;
        };

        updateTimer();
        this.otpTimerInterval = setInterval(updateTimer, 1000);
    }

    // ======================== LOGOUT ========================
    async handleLogout() {
        try {
            await fetch('/api/logout', { method: 'POST' });
        } catch (err) {
            // Logout locally even if request fails
        }
        this.isAuthenticated = false;
        this.userEmail = '';
        this.historyOpen = false;

        // Reset UI
        const sidebar = document.getElementById('history-sidebar');
        if (sidebar) {
            sidebar.classList.remove('active');
            sidebar.setAttribute('aria-hidden', 'true');
        }
        const chatMessages = document.getElementById('chat-messages');
        if (chatMessages) chatMessages.innerHTML = '';
        const suggestions = document.getElementById('suggestions');
        if (suggestions) suggestions.innerHTML = '';

        this.showScreen('auth-screen');
        this.switchAuthTab('login');
    }

    // ======================== CHAT METHODS ========================
    async sendMessage(text) {
        text = (text || '').trim();
        if (!text || this.isTyping) return;

        // Add user message
        this.addMessage('user', text);

        // Clear input
        const input = document.getElementById('chat-input');
        if (input) {
            input.value = '';
            input.focus();
        }

        // Clear suggestions
        this.updateSuggestions([]);

        // Show typing indicator
        this.showTypingIndicator();

        // Random delay to simulate thinking (500-1500ms)
        const thinkDelay = 500 + Math.random() * 1000;

        try {
            const res = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text })
            });
            const data = await res.json();

            // Wait for minimum thinking delay
            await new Promise(resolve => setTimeout(resolve, thinkDelay));
            this.hideTypingIndicator();

            // Add bot response
            const msgType = data.type || 'text';
            this.addMessage('bot', data.response, msgType, data.data);

            // Update suggestions
            if (data.suggestions && data.suggestions.length > 0) {
                this.updateSuggestions(data.suggestions);
            }
        } catch (err) {
            await new Promise(resolve => setTimeout(resolve, thinkDelay));
            this.hideTypingIndicator();
            this.addMessage('bot', 'Sorry, I encountered a network error. Please try again.');
        }
    }

    addMessage(role, content, type = 'text', data = null, timestamp = null) {
        const container = document.getElementById('chat-messages');
        if (!container) return;

        let messageEl;

        if (role === 'user') {
            messageEl = this.createTextMessage('user', content, timestamp);
        } else {
            switch (type) {
                case 'options':
                    messageEl = this.createOptionsMessage(content, data, timestamp);
                    break;
                case 'comparison':
                    messageEl = this.createComparisonMessage(content, data, timestamp);
                    break;
                case 'summary':
                    messageEl = this.createSummaryMessage(content, data, timestamp);
                    break;
                case 'checklist':
                    messageEl = this.createChecklistMessage(content, data, timestamp);
                    break;
                default:
                    messageEl = this.createTextMessage('bot', content, timestamp);
            }
        }

        container.appendChild(messageEl);
        this.scrollToBottom();
    }

    createTextMessage(role, content, timestampVal = null) {
        const wrapper = document.createElement('div');
        wrapper.className = `message message--${role}`;

        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.setAttribute('aria-hidden', 'true');
        avatar.innerHTML = this.getAvatarHtml(role);

        const bubble = document.createElement('div');
        bubble.className = 'message-content';
        bubble.innerHTML = this.formatMessageText(content);

        const timestamp = document.createElement('span');
        timestamp.className = 'message-timestamp';
        timestamp.textContent = this.formatTimestamp(timestampVal);

        bubble.appendChild(timestamp);
        wrapper.appendChild(avatar);
        wrapper.appendChild(bubble);

        return wrapper;
    }

    createOptionsMessage(content, data, timestampVal = null) {
        const wrapper = document.createElement('div');
        wrapper.className = 'message message--bot';

        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.setAttribute('aria-hidden', 'true');
        avatar.innerHTML = this.getAvatarHtml('bot');

        const bubble = document.createElement('div');
        bubble.className = 'message-content';

        // Text content
        const textEl = document.createElement('div');
        textEl.innerHTML = this.formatMessageText(content);
        bubble.appendChild(textEl);

        // Options grid — use data if it's an array, otherwise fall back to parsing
        const optionsList = Array.isArray(data) ? data : [];
        if (optionsList.length > 0) {
            const grid = document.createElement('div');
            grid.className = 'options-grid';

            const icons = ['💼', '🏠', '📊', '💰', '📋', '🧮', '📈', '🎯', '💡', '🔍'];
            optionsList.forEach((opt, i) => {
                const label = typeof opt === 'string' ? opt : (opt.label || opt.text || String(opt));
                const card = document.createElement('button');
                card.className = 'option-card';
                card.innerHTML = `
                    <span class="option-card-icon">${icons[i % icons.length]}</span>
                    <span class="option-card-label">${this.escapeHtml(label)}</span>
                `;
                card.style.animationDelay = `${i * 0.08}s`;
                card.addEventListener('click', () => this.sendMessage(label));
                grid.appendChild(card);
            });
            bubble.appendChild(grid);
        }

        const timestamp = document.createElement('span');
        timestamp.className = 'message-timestamp';
        timestamp.textContent = this.formatTimestamp(timestampVal);
        bubble.appendChild(timestamp);

        wrapper.appendChild(avatar);
        wrapper.appendChild(bubble);
        return wrapper;
    }

    createComparisonMessage(content, data, timestampVal = null) {
        const wrapper = document.createElement('div');
        wrapper.className = 'message message--bot';

        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.setAttribute('aria-hidden', 'true');
        avatar.innerHTML = this.getAvatarHtml('bot');

        const bubble = document.createElement('div');
        bubble.className = 'message-content';
        bubble.style.maxWidth = '520px';

        // Text content
        if (content) {
            const textEl = document.createElement('div');
            textEl.innerHTML = this.formatMessageText(content);
            bubble.appendChild(textEl);
        }

        if (data) {
            const comp = data.comparison || data;
            const recommended = comp.recommended || '';
            const isNewRec = recommended.toLowerCase().includes('new');
            const isOldRec = recommended.toLowerCase().includes('old');

            const compWrapper = document.createElement('div');
            compWrapper.className = 'comparison-wrapper';

            compWrapper.innerHTML = `
                <div class="comparison-header">
                    <h3>📊 Tax Regime Comparison</h3>
                    <p>Based on your income details</p>
                </div>
                <div class="comparison-grid">
                    ${this.buildRegimeCard('New Regime', comp.new_regime, isNewRec)}
                    ${this.buildRegimeCard('Old Regime', comp.old_regime, isOldRec)}
                </div>
                <div class="comparison-savings">
                    <div class="savings-label">💰 You Save</div>
                    <div class="savings-amount">${this.formatCurrency(comp.savings || 0)}</div>
                    ${comp.reason ? `<div class="savings-reason">${this.escapeHtml(comp.reason)}</div>` : ''}
                </div>
            `;

            bubble.appendChild(compWrapper);

            // Animate numbers after render
            setTimeout(() => this.animateComparisonNumbers(compWrapper), 100);
        }

        const timestamp = document.createElement('span');
        timestamp.className = 'message-timestamp';
        timestamp.textContent = this.formatTimestamp(timestampVal);
        bubble.appendChild(timestamp);

        wrapper.appendChild(avatar);
        wrapper.appendChild(bubble);
        return wrapper;
    }

    buildRegimeCard(title, regime, isRecommended) {
        if (!regime) return '';

        const taxAmount = regime.total_tax || regime.tax_amount || regime.tax || 0;
        const grossIncome = regime.gross_income || regime.total_income || 0;
        const deductions = regime.total_deductions || regime.deductions || 0;
        const taxableIncome = regime.taxable_income || 0;
        const effectiveRate = regime.effective_rate || regime.eff_rate || 0;
        const cess = regime.cess || 0;

        return `
            <div class="regime-card ${isRecommended ? 'recommended' : ''}" role="region" aria-label="${title}${isRecommended ? ' - Recommended' : ''}">
                ${isRecommended ? '<div class="recommended-badge">⭐ RECOMMENDED</div>' : ''}
                <div class="regime-card-title">${this.escapeHtml(title)}</div>
                <div class="regime-amount">
                    <div class="regime-amount-label">Tax Payable</div>
                    <div class="regime-amount-value" data-target="${taxAmount}">${this.formatCurrency(0)}</div>
                </div>
                <div class="regime-details">
                    ${grossIncome ? `
                    <div class="regime-detail-row">
                        <span class="regime-detail-label">Gross Income</span>
                        <span class="regime-detail-value">${this.formatCurrency(grossIncome)}</span>
                    </div>` : ''}
                    ${deductions ? `
                    <div class="regime-detail-row">
                        <span class="regime-detail-label">Deductions</span>
                        <span class="regime-detail-value" style="color: #00c853;">-${this.formatCurrency(deductions)}</span>
                    </div>` : ''}
                    ${taxableIncome ? `
                    <div class="regime-detail-row">
                        <span class="regime-detail-label">Taxable Income</span>
                        <span class="regime-detail-value">${this.formatCurrency(taxableIncome)}</span>
                    </div>` : ''}
                    ${cess ? `
                    <div class="regime-detail-row">
                        <span class="regime-detail-label">Cess (4%)</span>
                        <span class="regime-detail-value">${this.formatCurrency(cess)}</span>
                    </div>` : ''}
                    ${effectiveRate ? `
                    <div class="regime-detail-row">
                        <span class="regime-detail-label">Effective Rate</span>
                        <span class="regime-detail-value" style="color: #00d2ff;">${effectiveRate}%</span>
                    </div>` : ''}
                </div>
            </div>
        `;
    }

    animateComparisonNumbers(container) {
        const amountEls = container.querySelectorAll('.regime-amount-value[data-target]');
        amountEls.forEach(el => {
            const target = parseFloat(el.dataset.target) || 0;
            this.animateNumber(el, 0, target, 1200);
        });
    }

    animateNumber(element, start, end, duration) {
        const startTime = performance.now();
        const update = (currentTime) => {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            // Ease out cubic
            const eased = 1 - Math.pow(1 - progress, 3);
            const current = Math.round(start + (end - start) * eased);
            element.textContent = this.formatCurrency(current);
            if (progress < 1) {
                requestAnimationFrame(update);
            }
        };
        requestAnimationFrame(update);
    }

    createSummaryMessage(content, data, timestampVal = null) {
        const wrapper = document.createElement('div');
        wrapper.className = 'message message--bot';

        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.setAttribute('aria-hidden', 'true');
        avatar.innerHTML = this.getAvatarHtml('bot');

        const bubble = document.createElement('div');
        bubble.className = 'message-content';

        if (content) {
            const textEl = document.createElement('div');
            textEl.innerHTML = this.formatMessageText(content);
            bubble.appendChild(textEl);
        }

        if (data) {
            const summaryCard = document.createElement('div');
            summaryCard.className = 'summary-card';

            let bodyHtml = '';
            if (typeof data === 'object' && !Array.isArray(data)) {
                Object.entries(data).forEach(([key, value]) => {
                    const label = key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
                    const isAmount = typeof value === 'number' && value > 100;
                    const displayValue = isAmount ? this.formatCurrency(value) : value;
                    const highlightClass = key.includes('savings') || key.includes('refund') ? ' highlight' : '';
                    bodyHtml += `
                        <div class="summary-item">
                            <span class="summary-item-label">${this.escapeHtml(label)}</span>
                            <span class="summary-item-value${highlightClass}">${this.escapeHtml(String(displayValue))}</span>
                        </div>
                    `;
                });
            }

            const effectiveRate = data.effective_rate || data.eff_rate || 0;

            summaryCard.innerHTML = `
                <div class="summary-card-header">
                    <h4>📋 Tax Summary</h4>
                </div>
                <div class="summary-card-body">
                    ${bodyHtml}
                    ${effectiveRate ? `
                    <div class="summary-progress">
                        <div class="summary-progress-label">
                            <span>Effective Tax Rate</span>
                            <span>${effectiveRate}%</span>
                        </div>
                        <div class="progress-bar">
                            <div class="progress-bar-fill" style="width: 0%;" data-width="${Math.min(effectiveRate, 100)}%"></div>
                        </div>
                    </div>` : ''}
                </div>
            `;

            bubble.appendChild(summaryCard);

            // Animate progress bar
            setTimeout(() => {
                const fill = summaryCard.querySelector('.progress-bar-fill');
                if (fill) fill.style.width = fill.dataset.width;
            }, 200);
        }

        const timestamp = document.createElement('span');
        timestamp.className = 'message-timestamp';
        timestamp.textContent = this.formatTimestamp(timestampVal);
        bubble.appendChild(timestamp);

        wrapper.appendChild(avatar);
        wrapper.appendChild(bubble);
        return wrapper;
    }

    createChecklistMessage(content, data, timestampVal = null) {
        const wrapper = document.createElement('div');
        wrapper.className = 'message message--bot';

        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.setAttribute('aria-hidden', 'true');
        avatar.innerHTML = this.getAvatarHtml('bot');

        const bubble = document.createElement('div');
        bubble.className = 'message-content';

        if (content) {
            const textEl = document.createElement('div');
            textEl.innerHTML = this.formatMessageText(content);
            bubble.appendChild(textEl);
        }

        if (data && Array.isArray(data)) {
            const checklist = document.createElement('div');
            checklist.className = 'checklist-card';
            checklist.innerHTML = `<div class="checklist-card-title">📄 Required Documents</div>`;

            const items = document.createElement('div');
            items.className = 'checklist-items';

            data.forEach((item, index) => {
                const isRequired = item.required !== false;
                const itemEl = document.createElement('div');
                itemEl.className = 'checklist-item';
                itemEl.style.animationDelay = `${index * 0.1}s`;
                itemEl.innerHTML = `
                    <div class="checklist-icon ${isRequired ? 'required' : 'optional'}">${isRequired ? '✓' : '○'}</div>
                    <div class="checklist-info">
                        <div class="checklist-doc">${this.escapeHtml(item.doc || item.name || 'Document')}</div>
                        ${item.reason ? `<div class="checklist-reason">${this.escapeHtml(item.reason)}</div>` : ''}
                    </div>
                    <span class="checklist-badge ${isRequired ? 'required' : 'optional'}">${isRequired ? 'Required' : 'Optional'}</span>
                `;
                items.appendChild(itemEl);
            });

            checklist.appendChild(items);
            bubble.appendChild(checklist);
        }

        const timestamp = document.createElement('span');
        timestamp.className = 'message-timestamp';
        timestamp.textContent = this.formatTimestamp(timestampVal);
        bubble.appendChild(timestamp);

        wrapper.appendChild(avatar);
        wrapper.appendChild(bubble);
        return wrapper;
    }

    // ======================== TYPING INDICATOR ========================
    showTypingIndicator() {
        this.isTyping = true;
        const indicator = document.getElementById('typing-indicator');
        if (indicator) {
            indicator.classList.remove('hidden');
            this.scrollToBottom();
        }
    }

    hideTypingIndicator() {
        this.isTyping = false;
        const indicator = document.getElementById('typing-indicator');
        if (indicator) indicator.classList.add('hidden');
    }

    // ======================== SUGGESTIONS ========================
    updateSuggestions(suggestions) {
        const container = document.getElementById('suggestions');
        if (!container) return;
        container.innerHTML = '';

        if (!suggestions || suggestions.length === 0) return;

        suggestions.forEach((text, i) => {
            const chip = document.createElement('button');
            chip.className = 'suggestion-chip';
            chip.textContent = text;
            chip.style.animationDelay = `${i * 0.08}s`;
            chip.addEventListener('click', () => this.sendMessage(text));
            container.appendChild(chip);
        });
    }

    // ======================== SCROLL ========================
    scrollToBottom() {
        const container = document.getElementById('chat-messages');
        if (container) {
            requestAnimationFrame(() => {
                container.scrollTo({
                    top: container.scrollHeight,
                    behavior: 'smooth'
                });
            });
        }
    }

    // ======================== HISTORY ========================
    toggleHistory() {
        const sidebar = document.getElementById('history-sidebar');
        if (!sidebar) return;

        this.historyOpen = !this.historyOpen;

        if (this.historyOpen) {
            sidebar.classList.add('active');
            sidebar.setAttribute('aria-hidden', 'false');
            this.loadHistory();
        } else {
            sidebar.classList.remove('active');
            sidebar.setAttribute('aria-hidden', 'true');
        }
    }

    async loadHistory() {
        const listEl = document.getElementById('history-list');
        const emptyEl = document.getElementById('history-empty');
        const loadingEl = document.getElementById('history-loading');

        if (!listEl) return;

        listEl.innerHTML = '';
        if (emptyEl) emptyEl.classList.add('hidden');
        if (loadingEl) loadingEl.classList.remove('hidden');

        try {
            const res = await fetch('/api/history');
            const responseData = await res.json();
            
            // Extract the session array from the returned {success: true, sessions: [...]} wrapper
            const sessions = (responseData && responseData.sessions) || [];

            if (loadingEl) loadingEl.classList.add('hidden');

            if (!Array.isArray(sessions) || sessions.length === 0) {
                if (emptyEl) emptyEl.classList.remove('hidden');
                return;
            }

            sessions.forEach((session, index) => {
                const card = document.createElement('div');
                card.className = 'history-card';
                card.setAttribute('role', 'listitem');
                card.style.animationDelay = `${index * 0.08}s`;

                const regimeLabel = session.recommended_regime || 'N/A';
                const isNew = regimeLabel.toLowerCase().includes('new');

                card.innerHTML = `
                    <div class="history-card-header">
                        <span class="history-card-date">${this.escapeHtml(session.date || '')}</span>
                        <span class="history-card-time">${this.escapeHtml(session.time || '')}</span>
                    </div>
                    <div class="history-card-body">
                        <div class="history-card-row">
                            <span class="history-card-label">Status</span>
                            <span class="badge badge-status">${this.escapeHtml(session.marital_status || 'N/A')}</span>
                        </div>
                        <div class="history-card-row">
                            <span class="history-card-label">Income</span>
                            <span class="history-card-value">${this.formatCurrency(session.total_income || 0)}</span>
                        </div>
                        <div class="history-card-row">
                            <span class="history-card-label">Tax (New)</span>
                            <span class="history-card-value">${this.formatCurrency(session.tax_new_regime || 0)}</span>
                        </div>
                        <div class="history-card-row">
                            <span class="history-card-label">Tax (Old)</span>
                            <span class="history-card-value">${this.formatCurrency(session.tax_old_regime || 0)}</span>
                        </div>
                        <div class="history-card-row">
                            <span class="history-card-label">Recommended</span>
                            <span class="badge ${isNew ? 'badge-new' : 'badge-old'}">${this.escapeHtml(regimeLabel)}</span>
                        </div>
                        ${session.savings ? `
                        <div class="history-card-row">
                            <span class="history-card-label">Savings</span>
                            <span class="badge badge-savings">💰 ${this.formatCurrency(session.savings)}</span>
                        </div>` : ''}
                    </div>
                `;

                card.addEventListener('click', () => this.viewSession(session.id));
                listEl.appendChild(card);
            });
        } catch (err) {
            if (loadingEl) loadingEl.classList.add('hidden');
            listEl.innerHTML = `<div class="sidebar-empty"><span>⚠️</span><p>Failed to load history. Please try again.</p></div>`;
        }
    }

    // ======================== SESSION DETAIL ========================
    async viewSession(sessionId) {
        const modal = document.getElementById('session-modal');
        const modalMessages = document.getElementById('session-modal-messages');
        const modalDate = document.getElementById('session-modal-date');
        const modalSummary = document.getElementById('session-modal-summary');

        if (!modal || !modalMessages) return;

        modal.classList.remove('hidden');
        modalMessages.innerHTML = '<div class="shimmer-block" style="height:60px;margin-bottom:12px;"></div><div class="shimmer-block" style="height:60px;margin-bottom:12px;"></div><div class="shimmer-block" style="height:60px;"></div>';
        if (modalSummary) modalSummary.innerHTML = '';

        try {
            const res = await fetch(`/api/session/${sessionId}`);
            const data = await res.json();

            modalMessages.innerHTML = '';

            if (modalDate && data.messages && data.messages.length > 0) {
                modalDate.textContent = data.messages[0].timestamp || '';
            }

            if (data.messages && Array.isArray(data.messages)) {
                data.messages.forEach(msg => {
                    const role = msg.role === 'user' ? 'user' : 'bot';
                    let el;

                    switch (msg.type) {
                        case 'options':
                            el = this.createOptionsMessage(msg.content, msg.data, msg.timestamp);
                            break;
                        case 'comparison':
                            el = this.createComparisonMessage(msg.content, msg.data, msg.timestamp);
                            break;
                        case 'summary':
                            el = this.createSummaryMessage(msg.content, msg.data, msg.timestamp);
                            break;
                        case 'checklist':
                            el = this.createChecklistMessage(msg.content, msg.data, msg.timestamp);
                            break;
                        default:
                            el = this.createTextMessage(role, msg.content, msg.timestamp);
                    }

                    // Remove animation for modal replay
                    el.style.animation = 'none';
                    modalMessages.appendChild(el);
                });
            }

            // Render summary
            if (data.summary && modalSummary) {
                modalSummary.innerHTML = `
                    <div class="summary-card">
                        <div class="summary-card-header"><h4>📋 Session Summary</h4></div>
                        <div class="summary-card-body">
                            ${Object.entries(data.summary).map(([key, value]) => {
                                const label = key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
                                const isAmount = typeof value === 'number' && value > 100;
                                return `
                                    <div class="summary-item">
                                        <span class="summary-item-label">${this.escapeHtml(label)}</span>
                                        <span class="summary-item-value">${isAmount ? this.formatCurrency(value) : this.escapeHtml(String(value))}</span>
                                    </div>
                                `;
                            }).join('')}
                        </div>
                    </div>
                `;
            }
        } catch (err) {
            modalMessages.innerHTML = '<div class="sidebar-empty"><span>⚠️</span><p>Failed to load session details.</p></div>';
        }
    }

    closeModal() {
        const modal = document.getElementById('session-modal');
        if (modal) modal.classList.add('hidden');
    }

    // ======================== NEW SESSION ========================
    async startNewSession() {
        const chatMessages = document.getElementById('chat-messages');
        if (chatMessages) chatMessages.innerHTML = '';
        this.updateSuggestions([]);

        this.showTypingIndicator();

        try {
            const res = await fetch('/api/new-session', { method: 'POST' });
            const data = await res.json();

            await new Promise(resolve => setTimeout(resolve, 600));
            this.hideTypingIndicator();

            const msgType = data.type || 'text';
            this.addMessage('bot', data.response, msgType, data.data);

            if (data.suggestions && data.suggestions.length > 0) {
                this.updateSuggestions(data.suggestions);
            }
        } catch (err) {
            await new Promise(resolve => setTimeout(resolve, 600));
            this.hideTypingIndicator();
            this.addMessage('bot', 'Welcome! I\'m TaxBot, your AI-powered tax filing assistant. How can I help you today?');
        }
    }

    // ======================== UTILITY METHODS ========================
    getAvatarHtml(role) {
        if (role === 'bot') {
            return `<svg class="avatar-svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="color:#ffffff;display:block;"><path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/><path d="M2 14h2"/><path d="M20 14h2"/><path d="M15 13v2"/><path d="M9 13v2"/></svg>`;
        } else {
            return `<svg class="avatar-svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="color:#ffffff;display:block;"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>`;
        }
    }

    formatCurrency(amount) {
        const num = Number(amount);
        if (isNaN(num)) return '₹0';
        return '₹' + num.toLocaleString('en-IN', { maximumFractionDigits: 0 });
    }

    formatTimestamp(serverTime) {
        let dateObj;
        if (serverTime) {
            // SQLite CURRENT_TIMESTAMP has format YYYY-MM-DD HH:MM:SS in UTC
            // Append " UTC" to parse it as UTC rather than naive local time
            const parsedTime = typeof serverTime === 'string' && !serverTime.includes('Z') && !serverTime.includes('+')
                ? serverTime + ' UTC'
                : serverTime;
            dateObj = new Date(parsedTime);
            if (isNaN(dateObj.getTime())) {
                dateObj = new Date();
            }
        } else {
            dateObj = new Date();
        }
        let hours = dateObj.getHours();
        const minutes = String(dateObj.getMinutes()).padStart(2, '0');
        const ampm = hours >= 12 ? 'PM' : 'AM';
        hours = hours % 12 || 12;
        return `${hours}:${minutes} ${ampm}`;
    }

    formatMessageText(text) {
        if (!text) return '';
        let escaped = this.escapeHtml(text);
        // Bold: **text**
        escaped = escaped.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        // Newlines
        escaped = escaped.replace(/\n/g, '<br>');
        return escaped;
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    showAuthMessage(message, type) {
        const msgEl = document.getElementById('auth-message');
        if (!msgEl) return;

        msgEl.textContent = message;
        msgEl.className = `auth-message ${type}`;
        msgEl.classList.remove('hidden');

        if (type === 'error') {
            msgEl.classList.add('shake');
            setTimeout(() => msgEl.classList.remove('shake'), 500);
        }

        // Auto-hide success messages
        if (type === 'success') {
            setTimeout(() => this.clearAuthMessage(), 5000);
        }
    }

    clearAuthMessage() {
        const msgEl = document.getElementById('auth-message');
        if (msgEl) msgEl.classList.add('hidden');
    }

    setButtonLoading(btn, loading) {
        if (!btn) return;
        const span = btn.querySelector('span:first-child');
        const loader = btn.querySelector('.btn-loader');

        if (loading) {
            btn.disabled = true;
            if (span) span.style.opacity = '0.5';
            if (loader) loader.classList.remove('hidden');
        } else {
            btn.disabled = false;
            if (span) span.style.opacity = '1';
            if (loader) loader.classList.add('hidden');
        }
    }
}

// ======================== INIT ========================
document.addEventListener('DOMContentLoaded', () => {
    window.taxBot = new TaxBotApp();
});
