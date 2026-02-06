// API 调用封装
class API {
    constructor() {
        // 根据当前环境自动判断API地址
        const isProduction = window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1';
        const port = window.location.port || '80';
        const isStaticServer = port === '8000' || window.location.protocol === 'file:';

        // 如果通过静态文件服务器访问，使用相对路径
        if (isStaticServer) {
            this.baseURL = '/api/v1';
        } else if (isProduction) {
            this.baseURL = '/api/v1';
        } else {
            // 开发环境：假设后端运行在8000端口
            this.baseURL = 'http://localhost:8000/api/v1';
        }

        this.timeout = 30000;

        // 调试信息
        console.log('API initialized:', {
            hostname: window.location.hostname,
            port: window.location.port,
            protocol: window.location.protocol,
            href: window.location.href,
            isProduction,
            isStaticServer,
            baseURL: this.baseURL
        });
    }

    // 获取认证头
    getAuthHeaders() {
        const token = localStorage.getItem('access_token');
        return token ? { 'Authorization': `Bearer ${token}` } : {};
    }

    // 通用请求方法
    async request(method, path, data = null, options = {}) {
        const url = `${this.baseURL}${path}`;
        console.log(`API Request: ${method} ${url}`, data); // 调试信息
        
        const headers = {
            'Content-Type': 'application/json',
            ...this.getAuthHeaders(),
            ...options.headers
        };

        const config = {
            method,
            headers,
            ...options
        };

        if (data && method !== 'GET') {
            config.body = JSON.stringify(data);
        }

        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), this.timeout);
            
            config.signal = controller.signal;
            
            const response = await fetch(url, config);
            clearTimeout(timeoutId);

            if (response.status === 401) {
                // 认证失败，清除token并跳转登录
                localStorage.removeItem('access_token');
                localStorage.removeItem('user_role');
                window.location.href = '/';
                return;
            }

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.error?.message || `HTTP ${response.status}`);
            }

            return result;
        } catch (error) {
            console.error('API Request failed:', error); // 调试信息
            if (error.name === 'AbortError') {
                throw new Error('请求超时');
            }
            throw error;
        }
    }

    // GET 请求
    async get(path, params = {}) {
        const queryString = new URLSearchParams(params).toString();
        const fullPath = queryString ? `${path}?${queryString}` : path;
        return this.request('GET', fullPath);
    }

    // POST 请求
    async post(path, data) {
        return this.request('POST', path, data);
    }

    // PUT 请求
    async put(path, data) {
        return this.request('PUT', path, data);
    }

    // DELETE 请求
    async delete(path) {
        return this.request('DELETE', path);
    }

    // 文件上传
    async upload(path, file, extraFields = {}) {
        const formData = new FormData();
        formData.append('file', file);
        
        for (const [key, value] of Object.entries(extraFields)) {
            formData.append(key, value);
        }

        const headers = this.getAuthHeaders();
        delete headers['Content-Type']; // 让浏览器自动设置

        try {
            const response = await fetch(`${this.baseURL}${path}`, {
                method: 'POST',
                headers,
                body: formData
            });

            if (response.status === 401) {
                localStorage.removeItem('access_token');
                localStorage.removeItem('user_role');
                window.location.href = '/';
                return;
            }

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.error?.message || `HTTP ${response.status}`);
            }

            return result;
        } catch (error) {
            throw error;
        }
    }
}

// 创建全局API实例
const api = new API();

// 认证相关API
const authAPI = {
    async login(username, password) {
        return api.post('/auth/login', { username, password });
    },

    async register(username, password, role = 'student') {
        return api.post('/auth/register', { username, password, role });
    },

    async getCurrentUser() {
        return api.get('/auth/me');
    }
};

// 知识库相关API
const kbAPI = {
    async uploadDocument(file, courseId) {
        return api.upload('/kb/upload', file, { course_id: courseId });
    },

    async ingestDocument(documentId, chunkPolicy = null) {
        return api.post('/kb/ingest', { 
            document_id: documentId, 
            chunk_policy: chunkPolicy 
        });
    },

    async getTaskStatus(taskId) {
        return api.get(`/kb/tasks/${taskId}`);
    },

    async searchKnowledge(query, courseId, topK = 12) {
        return api.get('/kb/search', { 
            q: query, 
            course_id: courseId, 
            top_k: topK 
        });
    }
};

// 问答相关API
const qaAPI = {
    async askQuestion(courseId, question, topK = 12) {
        return api.post('/qa/ask', { 
            course_id: courseId, 
            question, 
            top_k: topK 
        });
    },

    async addFeedback(qaId, rating) {
        return api.post('/qa/feedback', { 
            qa_id: qaId, 
            rating 
        });
    },

    // WebSocket连接
    connectStream() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        // 根据当前环境确定WebSocket地址
        const isStaticServer = (window.location.port || '80') === '8000' || window.location.protocol === 'file:';
        let wsUrl;

        if (isStaticServer) {
            wsUrl = `${protocol}//${window.location.host}/api/v1/qa/stream`;
        } else {
            // 开发环境：连接到后端服务器
            wsUrl = `ws://localhost:8000/api/v1/qa/stream`;
        }

        console.log('WebSocket connecting to:', wsUrl);
        return new WebSocket(wsUrl);
    }
};

// 推荐相关API
const recAPI = {
    async getRecommendationByQuestion(question, courseId) {
        return api.get('/rec/by_question', { 
            q: question, 
            course_id: courseId 
        });
    },

    async getRecommendationByProfile(userId, courseId) {
        const params = { course_id: courseId };
        if (userId) params.user_id = userId;
        return api.get('/rec/by_profile', params);
    }
};

// 分析相关API
const analyticsAPI = {
    async recordEvent(userId, courseId, eventType, payload = {}) {
        return api.post('/analytics/event', {
            user_id: userId,
            course_id: courseId,
            event_type: eventType,
            payload: payload || {},
            ts: new Date().toISOString()
        });
    },

    async getStudentProfile(userId, courseId) {
        return api.get(`/analytics/student/${userId}`, { 
            course_id: courseId 
        });
    },

    async getClassDashboard(courseId) {
        return api.get(`/analytics/class/${courseId}`);
    }
};

// 错误处理工具
function handleAPIError(error, context = '') {
    console.error(`API Error ${context}:`, error);
    
    let message = '操作失败';
    if (error.message) {
        message = error.message;
    }
    
    showToast(message, 'error');
    return null;
}