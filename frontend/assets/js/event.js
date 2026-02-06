// 事件记录和埋点
class EventTracker {
    constructor() {
        this.courseId = getDefaultCourseId();
        this.sessionEvents = [];
        this.batchSize = 10;
        this.flushInterval = 30000; // 30秒
        
        // 启动定时批量上报
        this.startBatchReporting();
        
        // 页面卸载时上报剩余事件
        window.addEventListener('beforeunload', () => {
            this.flushEvents(true);
        });
    }

    // 记录事件
    async recordEvent(eventType, payload = {}, immediate = false) {
        // 如果用户未登录，只记录到本地，不发送到服务器
        if (!auth || !auth.isAuthenticated()) {
            console.log('Event recorded locally (not logged in):', eventType, payload);
            return;
        }

        // 获取用户ID，如果没有则不发送
        const userId = auth.getCurrentUserId();
        if (!userId) {
            console.log('Event not sent (user ID not available):', eventType);
            return;
        }

        const event = {
            user_id: userId,
            course_id: this.courseId,
            event_type: eventType,
            payload: {
                ...payload,
                timestamp: Date.now(),
                page: window.location.pathname,
                user_agent: navigator.userAgent.substring(0, 200)
            }
        };

        if (immediate) {
            // 立即上报
            try {
                await analyticsAPI.recordEvent(
                    event.user_id,
                    event.course_id,
                    event.event_type,
                    event.payload
                );
            } catch (error) {
                console.warn('Failed to record event immediately:', error);
            }
        } else {
            // 加入批量队列
            this.sessionEvents.push(event);
            
            // 如果队列满了，立即上报
            if (this.sessionEvents.length >= this.batchSize) {
                this.flushEvents();
            }
        }
    }

    // 批量上报事件
    async flushEvents(sync = false) {
        if (this.sessionEvents.length === 0) {
            return;
        }

        const eventsToSend = [...this.sessionEvents];
        this.sessionEvents = [];

        try {
            // 批量发送事件
            const promises = eventsToSend.map(event => 
                analyticsAPI.recordEvent(
                    event.user_id,
                    event.course_id,
                    event.event_type,
                    event.payload
                )
            );

            if (sync) {
                // 同步等待（页面卸载时）
                await Promise.all(promises);
            } else {
                // 异步发送
                Promise.all(promises).catch(error => {
                    console.warn('Failed to flush events:', error);
                    // 失败的事件重新加入队列
                    this.sessionEvents.unshift(...eventsToSend);
                });
            }
        } catch (error) {
            console.warn('Failed to flush events:', error);
        }
    }

    // 启动定时批量上报
    startBatchReporting() {
        setInterval(() => {
            this.flushEvents();
        }, this.flushInterval);
    }

    // 页面访问事件
    trackPageView(pageName, additionalData = {}) {
        this.recordEvent('page_view', {
            page_name: pageName,
            referrer: document.referrer,
            ...additionalData
        });
    }

    // 搜索事件
    trackSearch(query, resultCount = 0, additionalData = {}) {
        this.recordEvent('search', {
            query,
            result_count: resultCount,
            query_length: query.length,
            ...additionalData
        });
    }

    // 点击搜索结果事件
    trackSearchResultClick(chunkId, position, score, additionalData = {}) {
        this.recordEvent('click_result', {
            chunk_id: chunkId,
            position,
            score,
            ...additionalData
        });
    }

    // 问答事件
    trackQuestion(question, mode = 'rest', additionalData = {}) {
        this.recordEvent('ask', {
            question,
            mode,
            question_length: question.length,
            ...additionalData
        });
    }

    // 问答反馈事件
    trackFeedback(qaId, rating, confidence, additionalData = {}) {
        this.recordEvent('feedback', {
            qa_id: qaId,
            rating,
            confidence,
            ...additionalData
        });
    }

    // 查看推荐事件
    trackViewRecommendation(recommendationType, itemCount, additionalData = {}) {
        this.recordEvent('view_recommend', {
            recommendation_type: recommendationType,
            item_count: itemCount,
            ...additionalData
        });
    }

    // 点击推荐项事件
    trackRecommendationClick(item, itemType, additionalData = {}) {
        this.recordEvent('click_recommend_item', {
            item,
            item_type: itemType,
            ...additionalData
        });
    }

    // 查看学情画像事件
    trackViewProfile(userId, riskLevel, weakKpCount, additionalData = {}) {
        this.recordEvent('view_profile', {
            viewed_user_id: userId,
            risk_level: riskLevel,
            weak_kp_count: weakKpCount,
            ...additionalData
        });
    }

    // 文档上传事件
    trackDocumentUpload(fileName, fileSize, fileType, additionalData = {}) {
        this.recordEvent('upload_document', {
            file_name: fileName,
            file_size: fileSize,
            file_type: fileType,
            ...additionalData
        });
    }

    // 学习时长跟踪
    trackLearningTime(startTime, endTime, activity, additionalData = {}) {
        const duration = endTime - startTime;
        this.recordEvent('learning_time', {
            activity,
            duration_ms: duration,
            start_time: startTime,
            end_time: endTime,
            ...additionalData
        });
    }

    // 错误事件
    trackError(errorType, errorMessage, context, additionalData = {}) {
        this.recordEvent('error', {
            error_type: errorType,
            error_message: errorMessage.substring(0, 500),
            context,
            ...additionalData
        }, true); // 错误事件立即上报
    }
}

// 创建全局事件跟踪器
const eventTracker = new EventTracker();

// 便捷的事件记录函数
function recordEvent(eventType, payload = {}) {
    eventTracker.recordEvent(eventType, payload);
}

// 页面级别的事件跟踪
class PageTracker {
    constructor(pageName) {
        this.pageName = pageName;
        this.startTime = Date.now();
        this.interactions = 0;
        
        // 记录页面访问
        eventTracker.trackPageView(pageName);
        
        // 绑定通用事件
        this.bindCommonEvents();
    }

    bindCommonEvents() {
        // 点击事件
        document.addEventListener('click', (e) => {
            this.interactions++;
            
            // 记录按钮点击
            if (e.target.tagName === 'BUTTON' || e.target.classList.contains('btn')) {
                recordEvent('button_click', {
                    button_text: e.target.textContent.trim(),
                    button_class: e.target.className,
                    page: this.pageName
                });
            }
            
            // 记录链接点击
            if (e.target.tagName === 'A') {
                recordEvent('link_click', {
                    link_text: e.target.textContent.trim(),
                    link_href: e.target.href,
                    page: this.pageName
                });
            }
        });

        // 表单提交事件
        document.addEventListener('submit', (e) => {
            recordEvent('form_submit', {
                form_id: e.target.id,
                form_class: e.target.className,
                page: this.pageName
            });
        });

        // 页面卸载时记录停留时长
        window.addEventListener('beforeunload', () => {
            const duration = Date.now() - this.startTime;
            eventTracker.trackLearningTime(
                this.startTime,
                Date.now(),
                this.pageName,
                { interactions: this.interactions }
            );
        });
    }

    // 记录特定页面事件
    trackPageEvent(eventType, payload = {}) {
        recordEvent(eventType, {
            ...payload,
            page: this.pageName
        });
    }
}

// 自动错误跟踪
window.addEventListener('error', (e) => {
    eventTracker.trackError(
        'javascript_error',
        e.message,
        'global_error_handler',
        {
            filename: e.filename,
            lineno: e.lineno,
            colno: e.colno
        }
    );
});

// Promise 错误跟踪
window.addEventListener('unhandledrejection', (e) => {
    eventTracker.trackError(
        'promise_rejection',
        e.reason?.message || String(e.reason),
        'unhandled_promise_rejection'
    );
});

// 性能监控
function trackPerformance() {
    if ('performance' in window) {
        window.addEventListener('load', () => {
            setTimeout(() => {
                const perfData = performance.getEntriesByType('navigation')[0];
                if (perfData) {
                    recordEvent('page_performance', {
                        load_time: perfData.loadEventEnd - perfData.loadEventStart,
                        dom_ready: perfData.domContentLoadedEventEnd - perfData.domContentLoadedEventStart,
                        total_time: perfData.loadEventEnd - perfData.fetchStart
                    });
                }
            }, 0);
        });
    }
}

// 启动性能监控
trackPerformance();