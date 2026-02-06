// 动态创建登录和注册模态框
function createAuthModals() {
    // 检查是否已经存在
    if (document.getElementById('login-modal')) {
        return;
    }

    const modalsHTML = `
    <!-- 登录模态框 -->
    <div id="login-modal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h2 class="modal-title">🔐 用户登录</h2>
                <button class="close" type="button">&times;</button>
            </div>
            <div class="modal-body">
                <form id="login-form">
                    <div class="form-group">
                        <label for="username-input" class="form-label">用户名</label>
                        <input type="text" id="username-input" name="username" class="form-control" 
                               placeholder="请输入用户名" required>
                    </div>
                    <div class="form-group">
                        <label for="password-input" class="form-label">密码</label>
                        <input type="password" id="password-input" name="password" class="form-control" 
                               placeholder="请输入密码" required>
                    </div>
                    <div class="form-actions">
                        <button type="button" class="btn btn-secondary" onclick="showRegister()">注册账户</button>
                        <button type="submit" class="btn btn-primary">
                            <span class="login-text">登录</span>
                            <span class="loading" style="display: none;"></span>
                        </button>
                    </div>
                </form>
                
                <!-- 默认账户提示 -->
                <div style="margin-top: 1.5rem; padding: 1rem; background: var(--bg-secondary); border-radius: var(--radius-md); font-size: 0.875rem; color: var(--text-secondary);">
                    <div style="font-weight: 600; margin-bottom: 0.5rem; color: var(--text-primary);">💡 测试账户</div>
                    <div>学生：student / student123</div>
                    <div>教师：teacher / teacher123</div>
                    <div>管理员：admin / admin123</div>
                </div>
            </div>
        </div>
    </div>

    <!-- 注册模态框 -->
    <div id="register-modal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h2 class="modal-title">📝 用户注册</h2>
                <button class="close" type="button">&times;</button>
            </div>
            <div class="modal-body">
                <form id="register-form">
                    <div class="form-group">
                        <label for="reg-username" class="form-label">用户名</label>
                        <input type="text" id="reg-username" name="username" class="form-control" 
                               placeholder="请输入用户名（3-50字符）" required>
                    </div>
                    <div class="form-group">
                        <label for="reg-password" class="form-label">密码</label>
                        <input type="password" id="reg-password" name="password" class="form-control" 
                               placeholder="请输入密码（至少6位）" required>
                    </div>
                    <div class="form-group">
                        <label for="role" class="form-label">角色</label>
                        <select id="role" name="role" class="form-control">
                            <option value="student">🎓 学生</option>
                            <option value="teacher">👨‍🏫 教师</option>
                        </select>
                    </div>
                    <div class="form-actions">
                        <button type="button" class="btn btn-secondary" onclick="showLogin()">返回登录</button>
                        <button type="submit" class="btn btn-primary">
                            <span class="register-text">注册</span>
                            <span class="loading" style="display: none;"></span>
                        </button>
                    </div>
                </form>
            </div>
        </div>
    </div>
    `;

    // 添加到body
    document.body.insertAdjacentHTML('beforeend', modalsHTML);
}

// 页面加载时创建模态框
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', createAuthModals);
} else {
    createAuthModals();
}
