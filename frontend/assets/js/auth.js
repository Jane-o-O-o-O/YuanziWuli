// 认证管理
class AuthManager {
    constructor() {
        this.token = localStorage.getItem('access_token');
        this.userRole = localStorage.getItem('user_role');
        this.currentUser = null;
    }

    // 检查是否已登录
    isAuthenticated() {
        return !!this.token;
    }

    // 检查用户角色
    hasRole(role) {
        return this.userRole === role || this.userRole === 'admin';
    }

    // 登录
    async login(username, password) {
        try {
            console.log('尝试登录:', username);
            const response = await authAPI.login(username, password);
            console.log('登录响应:', response);
            
            this.token = response.access_token;
            this.userRole = response.role;
            
            localStorage.setItem('access_token', this.token);
            localStorage.setItem('user_role', this.userRole);
            
            // 获取用户详细信息
            await this.loadCurrentUser();
            
            return true;
        } catch (error) {
            console.error('登录失败:', error);
            handleAPIError(error, 'login');
            return false;
        }
    }

    // 注册
    async register(username, password, role = 'student') {
        try {
            await authAPI.register(username, password, role);
            showToast('注册成功，请登录', 'success');
            return true;
        } catch (error) {
            handleAPIError(error, 'register');
            return false;
        }
    }

    // 登出
    logout() {
        this.token = null;
        this.userRole = null;
        this.currentUser = null;
        
        localStorage.removeItem('access_token');
        localStorage.removeItem('user_role');
        
        window.location.href = '/';
    }

    // 加载当前用户信息
    async loadCurrentUser() {
        if (!this.isAuthenticated()) {
            return null;
        }

        try {
            this.currentUser = await authAPI.getCurrentUser();
            return this.currentUser;
        } catch (error) {
            console.error('Failed to load current user:', error);
            // 如果是401错误，清除token
            if (error.message && error.message.includes('401')) {
                this.logout();
            }
            return null;
        }
    }

    // 获取当前用户
    getCurrentUser() {
        return this.currentUser;
    }

    // 获取用户ID
    getCurrentUserId() {
        return this.currentUser?.id;
    }
}

// 创建全局认证管理器
const auth = new AuthManager();

// 页面初始化认证
async function initAuth() {
    console.log('开始初始化认证系统');
    
    // 检查登录状态
    if (auth.isAuthenticated()) {
        console.log('用户已登录，加载用户信息');
        try {
            await auth.loadCurrentUser();
            if (auth.getCurrentUser()) {
                updateUIForAuthenticatedUser();
            } else {
                console.log('加载用户信息失败，切换到未登录状态');
                updateUIForUnauthenticatedUser();
            }
        } catch (error) {
            console.error('初始化用户信息失败:', error);
            updateUIForUnauthenticatedUser();
        }
    } else {
        console.log('用户未登录');
        updateUIForUnauthenticatedUser();
    }

    // 绑定事件
    bindAuthEvents();
    console.log('认证系统初始化完成');
}

function updateUIForAuthenticatedUser() {
    const user = auth.getCurrentUser();
    const loginSection = document.getElementById('login-section');
    const userSection = document.getElementById('user-section');
    
    if (loginSection && userSection && user) {
        // 隐藏登录按钮，显示用户信息
        loginSection.style.display = 'none';
        userSection.style.display = 'flex';
        
        // 更新用户信息
        const usernameEl = document.getElementById('username');
        const userRoleEl = document.getElementById('user-role');
        const avatarTextEl = document.getElementById('avatar-text');
        
        if (usernameEl) usernameEl.textContent = user.username;
        if (userRoleEl) {
            const roleNames = {
                'admin': '管理员',
                'teacher': '教师',
                'student': '学生'
            };
            userRoleEl.textContent = roleNames[user.role] || user.role;
            userRoleEl.className = `user-role ${user.role}`;
        }
        if (avatarTextEl) {
            // 生成头像文字（用户名首字母）
            avatarTextEl.textContent = user.username.charAt(0).toUpperCase();
        }
    }

    // 显示/隐藏基于角色的元素
    const teacherElements = document.querySelectorAll('.teacher-only');
    teacherElements.forEach(el => {
        el.style.display = auth.hasRole('teacher') ? 'block' : 'none';
    });

    const adminElements = document.querySelectorAll('.admin-only');
    adminElements.forEach(el => {
        el.style.display = auth.hasRole('admin') ? 'block' : 'none';
    });
}

function updateUIForUnauthenticatedUser() {
    console.log('更新UI为未登录状态');
    const loginSection = document.getElementById('login-section');
    const userSection = document.getElementById('user-section');
    
    if (loginSection && userSection) {
        // 显示登录按钮，隐藏用户信息
        loginSection.style.display = 'flex';
        userSection.style.display = 'none';
    }

    // 隐藏需要权限的元素
    const teacherElements = document.querySelectorAll('.teacher-only');
    teacherElements.forEach(el => {
        el.style.display = 'none';
    });

    const adminElements = document.querySelectorAll('.admin-only');
    adminElements.forEach(el => {
        el.style.display = 'none';
    });
}

function bindAuthEvents() {
    // 登录按钮事件
    const loginBtn = document.getElementById('login-btn');
    if (loginBtn) {
        console.log('绑定登录按钮事件');
        loginBtn.addEventListener('click', function(e) {
            console.log('登录按钮被点击');
            e.preventDefault();
            showLogin();
        });
    } else {
        console.log('未找到登录按钮');
    }

    // 退出按钮事件
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', () => {
            if (confirm('确定要退出登录吗？')) {
                auth.logout();
            }
        });
    }

    // 用户头像点击事件（已禁用）
    // const userAvatar = document.getElementById('user-avatar');
    // if (userAvatar) {
    //     userAvatar.addEventListener('click', showUserMenu);
    // }

    // 登录表单
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        console.log('绑定登录表单事件');
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            console.log('登录表单提交');
            
            const submitBtn = loginForm.querySelector('button[type="submit"]');
            const loginText = submitBtn.querySelector('.login-text');
            const loading = submitBtn.querySelector('.loading');
            
            // 显示加载状态
            if (loginText) loginText.style.display = 'none';
            if (loading) loading.style.display = 'inline-block';
            submitBtn.disabled = true;
            
            try {
                const username = document.getElementById('username-input').value;
                const password = document.getElementById('password-input').value;
                
                console.log('登录信息:', { username, password: '***' });
                
                const success = await auth.login(username, password);
                if (success) {
                    console.log('登录成功');
                    const loginModal = document.getElementById('login-modal');
                    hideModal(loginModal);
                    updateUIForAuthenticatedUser();
                    showToast('登录成功！欢迎回来', 'success');
                    
                    // 刷新页面或重定向
                    setTimeout(() => {
                        window.location.reload();
                    }, 1000);
                } else {
                    console.log('登录失败');
                }
            } catch (error) {
                console.error('登录过程出错:', error);
                showToast('登录过程出现错误', 'error');
            } finally {
                // 恢复按钮状态
                if (loginText) loginText.style.display = 'inline';
                if (loading) loading.style.display = 'none';
                submitBtn.disabled = false;
            }
        });
    } else {
        console.log('未找到登录表单');
    }

    // 注册表单
    const registerForm = document.getElementById('register-form');
    if (registerForm) {
        registerForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const submitBtn = registerForm.querySelector('button[type="submit"]');
            const registerText = submitBtn.querySelector('.register-text');
            const loading = submitBtn.querySelector('.loading');
            
            // 显示加载状态
            registerText.style.display = 'none';
            loading.style.display = 'inline-block';
            submitBtn.disabled = true;
            
            try {
                const username = document.getElementById('reg-username').value;
                const password = document.getElementById('reg-password').value;
                const role = document.getElementById('role').value;
                
                const success = await auth.register(username, password, role);
                if (success) {
                    const registerModal = document.getElementById('register-modal');
                    hideModal(registerModal);
                    showLogin();
                }
            } finally {
                // 恢复按钮状态
                registerText.style.display = 'inline';
                loading.style.display = 'none';
                submitBtn.disabled = false;
            }
        });
    }

    // 模态框关闭事件
    const closeButtons = document.querySelectorAll('.close');
    closeButtons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            const modal = e.target.closest('.modal');
            hideModal(modal);
        });
    });

    // 点击模态框外部关闭
    window.addEventListener('click', (e) => {
        if (e.target.classList.contains('modal')) {
            hideModal(e.target);
        }
    });
}

// 显示登录模态框
function showLogin() {
    console.log('显示登录模态框');
    const modal = document.getElementById('login-modal');
    if (modal) {
        modal.classList.add('show');
        const usernameInput = document.getElementById('username-input');
        if (usernameInput) {
            setTimeout(() => usernameInput.focus(), 100);
        }
    } else {
        console.error('未找到登录模态框');
    }
}

// 显示注册模态框
function showRegister() {
    const loginModal = document.getElementById('login-modal');
    const registerModal = document.getElementById('register-modal');
    
    if (loginModal) hideModal(loginModal);
    if (registerModal) {
        registerModal.classList.add('show');
        document.getElementById('reg-username').focus();
    }
}

// 隐藏模态框
function hideModal(modal) {
    if (modal) {
        modal.classList.remove('show');
        
        // 清空表单
        const forms = modal.querySelectorAll('form');
        forms.forEach(form => form.reset());
    }
}

// 显示用户菜单
function showUserMenu() {
    const user = auth.getCurrentUser();
    if (!user) return;
    
    // 创建用户菜单
    const existingMenu = document.querySelector('.user-menu');
    if (existingMenu) {
        existingMenu.remove();
        return;
    }
    
    const menu = document.createElement('div');
    menu.className = 'user-menu';
    menu.innerHTML = `
        <div class="user-menu-content">
            <div class="user-menu-header">
                <div class="user-avatar-large">
                    <span>${user.username.charAt(0).toUpperCase()}</span>
                </div>
                <div class="user-menu-info">
                    <div class="user-menu-name">${user.username}</div>
                    <div class="user-menu-role">${getRoleName(user.role)}</div>
                </div>
            </div>
            <div class="user-menu-actions">
                <a href="profile.html" class="user-menu-item">
                    <span>📊</span> 学情分析
                </a>
                <div class="user-menu-item" onclick="auth.logout()">
                    <span>🚪</span> 退出登录
                </div>
            </div>
        </div>
    `;
    
    // 添加样式
    menu.style.cssText = `
        position: fixed;
        top: 70px;
        right: 20px;
        background: var(--bg-card);
        border: 1px solid var(--border-light);
        border-radius: var(--radius-lg);
        box-shadow: var(--shadow-xl);
        z-index: 1000;
        min-width: 200px;
        animation: slideDown 0.2s ease-out;
    `;
    
    document.body.appendChild(menu);
    
    // 点击外部关闭菜单
    setTimeout(() => {
        document.addEventListener('click', function closeMenu(e) {
            if (!menu.contains(e.target)) {
                menu.remove();
                document.removeEventListener('click', closeMenu);
            }
        });
    }, 100);
}

// 获取角色中文名称
function getRoleName(role) {
    const roleNames = {
        'admin': '管理员',
        'teacher': '教师',
        'student': '学生'
    };
    return roleNames[role] || role;
}

// 检查页面访问权限
function checkPageAccess(requiredRole = null) {
    if (!auth.isAuthenticated()) {
        showToast('请先登录', 'warning');
        showLogin();
        return false;
    }

    if (requiredRole && !auth.hasRole(requiredRole)) {
        showToast('权限不足', 'error');
        window.location.href = '/';
        return false;
    }

    return true;
}

// 获取默认课程ID
function getDefaultCourseId() {
    return 1; // 原子物理学课程ID
}

// 添加用户菜单样式
if (!document.querySelector('#user-menu-styles')) {
    const style = document.createElement('style');
    style.id = 'user-menu-styles';
    style.textContent = `
        .user-menu-content {
            padding: var(--space-lg);
        }
        
        .user-menu-header {
            display: flex;
            align-items: center;
            gap: var(--space-md);
            margin-bottom: var(--space-lg);
            padding-bottom: var(--space-lg);
            border-bottom: 1px solid var(--border-light);
        }
        
        .user-avatar-large {
            width: 50px;
            height: 50px;
            border-radius: var(--radius-full);
            background: linear-gradient(135deg, var(--primary-main) 0%, var(--accent-gold) 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: 600;
            font-size: 1.2rem;
        }
        
        .user-menu-info {
            flex: 1;
        }
        
        .user-menu-name {
            font-weight: 600;
            color: var(--text-primary);
            margin-bottom: var(--space-xs);
        }
        
        .user-menu-role {
            font-size: 0.875rem;
            color: var(--text-secondary);
        }
        
        .user-menu-actions {
            display: flex;
            flex-direction: column;
            gap: var(--space-xs);
        }
        
        .user-menu-item {
            display: flex;
            align-items: center;
            gap: var(--space-sm);
            padding: var(--space-sm) var(--space-md);
            border-radius: var(--radius-md);
            color: var(--text-primary);
            text-decoration: none;
            transition: all var(--transition-fast);
            cursor: pointer;
        }
        
        .user-menu-item:hover {
            background: var(--bg-secondary);
            color: var(--primary-main);
        }
    `;
    document.head.appendChild(style);
}