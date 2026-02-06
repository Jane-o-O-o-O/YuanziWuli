# 原子物理智能课堂系统

基于RAG（检索增强生成）技术的原子物理学智能问答和个性化学习推荐系统。

## 🌟 系统特性

### 核心功能
- **智能问答**: 基于知识库的精准问答，提供引用证据和置信度评估
- **知识检索**: 快速搜索原子物理学相关知识点和概念
- **学习推荐**: 个性化学习路径和知识点推荐
- **学情分析**: 学习进度跟踪、薄弱点分析和风险预警

### 技术特色
- **RAG架构**: 检索增强生成，确保答案准确性和可追溯性
- **多智能体**: QA智能体、推荐智能体、学情分析智能体协同工作
- **向量检索**: 基于Chroma的高效语义检索
- **流式问答**: 支持WebSocket实时流式回答
- **多模态文档**: 支持PDF、Word、PPT、Markdown等格式

## 🏗️ 系统架构

```
原子物理智能课堂系统
├── 前端 (Frontend)
│   ├── 原生HTML/CSS/JS
│   ├── 响应式设计
│   └── WebSocket支持
├── 后端 (Backend)
│   ├── FastAPI框架
│   ├── SQLAlchemy ORM
│   ├── 异步任务处理
│   └── RESTful API
├── AI服务层
│   ├── 硅基流动API集成
│   ├── RAG管线
│   └── 多智能体系统
└── 数据层
    ├── SQLite关系数据库
    ├── Chroma向量数据库
    └── 文件存储系统
```

## 🚀 快速开始

### 环境要求
- Python 3.10+
- 硅基流动API密钥

### 安装步骤

1. **克隆项目**
```bash
git clone <repository-url>
cd atomic-physics-classroom
```

2. **安装依赖**
```bash
pip install -r backend/requirements.txt
```

3. **配置环境**
   - 系统已预配置硅基流动API密钥
   - 如需修改，请编辑 `.env` 文件

4. **启动系统**

   **方式一：使用启动脚本（推荐）**
   ```bash
   # Windows
   start.bat
   
   # Linux/Mac
   chmod +x start.sh
   ./start.sh
   ```

   **方式二：使用Python脚本**
   ```bash
   python run.py
   ```

5. **访问系统**
   - 前端: http://localhost:3000
   - 后端API: http://localhost:8000
   - API文档: http://localhost:8000/docs

6. **测试系统**
   ```bash
   python test_system.py
   ```

### 默认账户
- **管理员**: admin / admin123
- **教师**: teacher / teacher123  
- **学生**: student / student123

## 📚 使用指南

### 学生端功能

#### 1. 知识检索
- 输入关键词搜索相关知识点
- 查看搜索结果和相关度评分
- 点击结果查看详细内容

#### 2. 智能问答
- 输入具体问题获得详细回答
- 查看答案置信度和引用来源
- 支持流式问答体验
- 对答案进行反馈评价

#### 3. 学习推荐
- 基于问题获得相关知识点推荐
- 查看个性化学习计划
- 获得前置知识、例题、易错点提示

#### 4. 学情分析
- 查看学习活跃度统计
- 了解薄弱知识点分布
- 获得学习建议和风险提醒

### 教师端功能

#### 1. 文档管理
- 上传课程资料（PDF、Word、PPT等）
- 监控文档处理进度
- 管理知识库内容

#### 2. 班级面板
- 查看班级整体学习情况
- 识别需要关注的学生
- 分析班级薄弱知识点分布

## 🔧 技术实现

### 后端架构

#### 核心服务
- **KBService**: 知识库管理，文档解析和向量化
- **RAGService**: 检索增强生成，问答处理
- **RecService**: 推荐算法，学习路径规划
- **AnalyticsService**: 学情分析，风险评估

#### 数据处理管线
1. **文档上传** → 文件存储
2. **文档解析** → 结构化文本提取
3. **文本分块** → 语义单元切分
4. **向量化** → 硅基流动Embedding API
5. **入库** → Chroma向量存储

#### RAG问答流程
1. **问题标准化** → 文本预处理
2. **向量检索** → 语义相似度匹配
3. **重排序** → 硅基流动Rerank API
4. **提示构建** → 证据整合
5. **答案生成** → 硅基流动LLM API
6. **置信度计算** → 多维度评估

### 前端架构

#### 页面结构
- **index.html**: 系统首页和导航
- **pages/search.html**: 知识检索界面
- **pages/qa.html**: 智能问答界面
- **pages/recommend.html**: 学习推荐界面
- **pages/profile.html**: 学情分析界面
- **pages/teacher.html**: 教师管理界面

#### 核心模块
- **api.js**: API调用封装
- **auth.js**: 用户认证管理
- **event.js**: 事件跟踪和埋点
- **utils.js**: 通用工具函数

## 📊 数据模型

### 关系数据库表结构
- **users**: 用户信息
- **courses**: 课程信息
- **documents**: 文档记录
- **chunks**: 文本块
- **qa_logs**: 问答日志
- **events**: 学习事件
- **alerts**: 预警信息

### 向量数据库Schema
- **chunk_id**: 文本块ID
- **course_id**: 课程ID
- **document_id**: 文档ID
- **section**: 章节信息
- **page**: 页码
- **chunk_text**: 文本内容
- **embedding**: 向量表示

## 🔍 API文档

### 认证接口
- `POST /api/v1/auth/login` - 用户登录
- `POST /api/v1/auth/register` - 用户注册
- `GET /api/v1/auth/me` - 获取当前用户信息

### 知识库接口
- `POST /api/v1/kb/upload` - 上传文档
- `POST /api/v1/kb/ingest` - 文档入库
- `GET /api/v1/kb/tasks/{task_id}` - 查询任务状态
- `GET /api/v1/kb/search` - 知识检索

### 问答接口
- `POST /api/v1/qa/ask` - 提交问题
- `POST /api/v1/qa/feedback` - 问答反馈
- `WebSocket /api/v1/qa/stream` - 流式问答

### 推荐接口
- `GET /api/v1/rec/by_question` - 基于问题推荐
- `GET /api/v1/rec/by_profile` - 基于画像推荐

### 分析接口
- `POST /api/v1/analytics/event` - 记录学习事件
- `GET /api/v1/analytics/student/{user_id}` - 学生画像
- `GET /api/v1/analytics/class/{course_id}` - 班级面板

## 🛠️ 开发指南

### 项目结构
```
atomic-physics-classroom/
├── backend/                 # 后端代码
│   ├── app/
│   │   ├── api/            # API路由
│   │   ├── core/           # 核心配置
│   │   ├── db/             # 数据库
│   │   ├── kb/             # 知识库处理
│   │   ├── models/         # 数据模型
│   │   └── services/       # 业务服务
│   ├── requirements.txt    # Python依赖
│   └── main.py            # 应用入口
├── frontend/               # 前端代码
│   ├── assets/            # 静态资源
│   ├── pages/             # 页面文件
│   └── index.html         # 首页
├── docs/                  # 项目文档
├── storage/               # 文件存储
├── logs/                  # 日志文件
├── .env                   # 环境配置
├── run.py                 # 启动脚本
└── README.md              # 项目说明
```

### 开发环境搭建
1. 安装Python 3.10+
2. 创建虚拟环境: `python -m venv venv`
3. 激活虚拟环境: `source venv/bin/activate` (Linux/Mac) 或 `venv\Scripts\activate` (Windows)
4. 安装依赖: `pip install -r backend/requirements.txt`
5. 配置环境变量
6. 运行系统: `python run.py`

### 代码规范
- 后端遵循PEP 8规范
- 前端使用ES6+语法
- 注释使用中文
- 提交信息使用中文

## 🔒 安全考虑

- JWT令牌认证
- 角色权限控制
- 输入验证和清理
- API请求频率限制
- 文件上传安全检查
- 错误信息脱敏

## 📈 性能优化

- 向量检索缓存
- 数据库查询优化
- 异步任务处理
- 前端资源压缩
- CDN加速（可选）

## 🐛 故障排查

### 常见问题
1. **API Key无效**: 检查`.env`文件中的硅基流动API密钥
2. **向量维度不匹配**: 确保embedding模型输出维度为1024
3. **Chroma连接失败**: 检查存储目录权限和磁盘空间
4. **内存不足**: 调整批处理大小和并发数

### 日志查看
- 应用日志: `logs/app.log`
- 错误日志: 控制台输出
- 访问日志: FastAPI自动记录

## 🤝 贡献指南

1. Fork项目
2. 创建特性分支: `git checkout -b feature/new-feature`
3. 提交更改: `git commit -am 'Add new feature'`
4. 推送分支: `git push origin feature/new-feature`
5. 提交Pull Request

## 📄 许可证

本项目采用MIT许可证 - 查看[LICENSE](LICENSE)文件了解详情。

## 📞 联系方式

如有问题或建议，请通过以下方式联系：
- 项目Issues
- 邮箱: [your-email@example.com]

---

**原子物理智能课堂系统** - 让学习更智能，让教育更精准！