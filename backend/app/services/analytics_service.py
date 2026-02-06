import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.models.orm import Event, QALog, Alert, User
from app.models.schemas import (
    StudentProfile, WeakKnowledgePoint, ClassDashboard, 
    WeakKPDistribution, ClassAlert
)

logger = logging.getLogger(__name__)


class AnalyticsService:
    """学情分析服务"""
    
    def __init__(self):
        # 风险评估阈值
        self.risk_thresholds = {
            "inactive_days": 3,  # 连续不活跃天数
            "repeat_question_count": 4,  # 重复问题次数
            "low_confidence_threshold": 0.55,  # 低置信度阈值
            "weak_kp_count": 2  # 薄弱知识点数量
        }
    
    async def record_event(
        self,
        db: Session,
        user_id: int,
        course_id: int,
        event_type: str,
        payload: Dict[str, Any],
        timestamp: Optional[datetime] = None
    ):
        """记录学习事件"""
        try:
            event = Event(
                user_id=user_id,
                course_id=course_id,
                event_type=event_type,
                payload_json=payload if isinstance(payload, dict) else {},
                ts=timestamp or datetime.utcnow()
            )
            
            db.add(event)
            db.commit()
            
            logger.info(f"学习事件已记录: user_id={user_id}, event_type={event_type}")
            
        except Exception as e:
            logger.error(f"记录学习事件失败: {e}")
            db.rollback()
    
    async def get_student_profile(
        self,
        db: Session,
        user_id: int,
        course_id: int
    ) -> StudentProfile:
        """获取学生画像"""
        try:
            # 计算近7天活跃度
            seven_days_ago = datetime.utcnow() - timedelta(days=7)
            active_7d = db.query(func.count(Event.id)).filter(
                Event.user_id == user_id,
                Event.course_id == course_id,
                Event.ts >= seven_days_ago
            ).scalar() or 0
            
            # 分析薄弱知识点
            weak_kp = await self._analyze_weak_knowledge_points(db, user_id, course_id)
            
            # 评估风险等级
            risk_level, reasons = await self._assess_risk_level(db, user_id, course_id, active_7d, weak_kp)
            
            # 生成学习建议
            suggestions = self._generate_suggestions(risk_level, weak_kp, active_7d)
            
            return StudentProfile(
                active_7d=active_7d,
                weak_kp=weak_kp,
                risk_level=risk_level,
                reasons=reasons,
                suggestions=suggestions
            )
            
        except Exception as e:
            logger.error(f"获取学生画像失败: {e}")
            return StudentProfile(
                active_7d=0,
                weak_kp=[],
                risk_level="low",
                reasons=[],
                suggestions=[]
            )
    
    async def get_class_dashboard(
        self,
        db: Session,
        course_id: int
    ) -> ClassDashboard:
        """获取班级面板"""
        try:
            # 统计薄弱知识点分布
            weak_kp_dist = await self._get_weak_kp_distribution(db, course_id)
            
            # 获取预警名单
            alerts = await self._get_class_alerts(db, course_id)
            
            return ClassDashboard(
                weak_kp_dist=weak_kp_dist,
                alerts=alerts
            )
            
        except Exception as e:
            logger.error(f"获取班级面板失败: {e}")
            return ClassDashboard(weak_kp_dist=[], alerts=[])
    
    async def _analyze_weak_knowledge_points(
        self,
        db: Session,
        user_id: int,
        course_id: int
    ) -> List[WeakKnowledgePoint]:
        """分析薄弱知识点"""
        try:
            # 获取最近30天的问答记录
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            qa_logs = db.query(QALog).filter(
                QALog.user_id == user_id,
                QALog.course_id == course_id,
                QALog.created_at >= thirty_days_ago
            ).all()
            
            # 简单的知识点提取和统计
            kp_stats = {}
            
            for qa_log in qa_logs:
                # 基于问题关键词提取知识点
                kps = self._extract_knowledge_points_from_question(qa_log.question)
                
                for kp in kps:
                    if kp not in kp_stats:
                        kp_stats[kp] = {"total_confidence": 0, "count": 0}
                    
                    kp_stats[kp]["total_confidence"] += qa_log.confidence
                    kp_stats[kp]["count"] += 1
            
            # 计算平均置信度并筛选薄弱知识点
            weak_points = []
            for kp, stats in kp_stats.items():
                if stats["count"] > 0:
                    avg_confidence = stats["total_confidence"] / stats["count"]
                    if avg_confidence < 0.7:  # 置信度低于0.7认为是薄弱点
                        weak_points.append(WeakKnowledgePoint(
                            kp=kp,
                            score=avg_confidence
                        ))
            
            # 按置信度排序，最薄弱的在前
            weak_points.sort(key=lambda x: x.score)
            
            return weak_points[:5]  # 返回最薄弱的5个
            
        except Exception as e:
            logger.error(f"分析薄弱知识点失败: {e}")
            return []
    
    def _extract_knowledge_points_from_question(self, question: str) -> List[str]:
        """从问题中提取知识点"""
        # 简单的关键词匹配
        keywords_map = {
            "原子结构": ["原子", "结构", "模型", "核外电子", "轨道", "电子云"],
            "波粒二象性": ["波粒二象性", "波动", "粒子", "双缝", "干涉", "衍射"],
            "量子数": ["量子数", "主量子数", "角量子数", "磁量子数", "自旋量子数"],
            "原子光谱": ["光谱", "谱线", "巴尔末", "莱曼", "发射", "吸收", "跃迁"],
            "电子自旋": ["自旋", "斯特恩", "格拉赫", "磁矩", "自旋轨道耦合"],
            "光电效应": ["光电效应", "光电子", "逸出功", "截止频率"],
            "康普顿散射": ["康普顿", "散射", "光子", "动量"],
            "不确定性原理": ["不确定性", "海森堡", "测量", "位置", "动量"],
            "能级跃迁": ["能级", "跃迁", "激发", "基态", "激发态"],
            "塞曼效应": ["塞曼", "磁场", "谱线分裂", "正常塞曼", "反常塞曼"]
        }
        
        matched_kps = []
        for kp, keywords in keywords_map.items():
            if any(keyword in question for keyword in keywords):
                matched_kps.append(kp)
        
        return matched_kps if matched_kps else ["其他"]
    
    async def _assess_risk_level(
        self,
        db: Session,
        user_id: int,
        course_id: int,
        active_7d: int,
        weak_kp: List[WeakKnowledgePoint]
    ) -> tuple:
        """评估风险等级"""
        reasons = []
        risk_score = 0
        
        # 检查活跃度
        if active_7d == 0:
            reasons.append("近7天无学习活动")
            risk_score += 3
        elif active_7d < 3:
            reasons.append("近7天学习活动较少")
            risk_score += 1
        
        # 检查连续不活跃天数
        inactive_days = await self._get_consecutive_inactive_days(db, user_id, course_id)
        if inactive_days >= self.risk_thresholds["inactive_days"]:
            reasons.append(f"连续{inactive_days}天未学习")
            risk_score += 2
        
        # 检查薄弱知识点数量
        if len(weak_kp) >= self.risk_thresholds["weak_kp_count"]:
            reasons.append(f"存在{len(weak_kp)}个薄弱知识点")
            risk_score += 1
        
        # 检查重复问题
        repeat_questions = await self._check_repeat_questions(db, user_id, course_id)
        if repeat_questions > 0:
            reasons.append(f"存在{repeat_questions}个重复提问的知识点")
            risk_score += 1
        
        # 确定风险等级
        if risk_score >= 4:
            risk_level = "high"
        elif risk_score >= 2:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        return risk_level, reasons
    
    async def _get_consecutive_inactive_days(
        self,
        db: Session,
        user_id: int,
        course_id: int
    ) -> int:
        """获取连续不活跃天数"""
        try:
            # 获取最近的学习事件
            latest_event = db.query(Event).filter(
                Event.user_id == user_id,
                Event.course_id == course_id
            ).order_by(Event.ts.desc()).first()
            
            if not latest_event:
                return 7  # 如果没有任何事件，返回7天
            
            # 计算距离最后一次活动的天数
            days_since_last_activity = (datetime.utcnow() - latest_event.ts).days
            return days_since_last_activity
            
        except Exception as e:
            logger.error(f"获取连续不活跃天数失败: {e}")
            return 0
    
    async def _check_repeat_questions(
        self,
        db: Session,
        user_id: int,
        course_id: int
    ) -> int:
        """检查重复问题"""
        try:
            # 获取最近7天的问答记录
            seven_days_ago = datetime.utcnow() - timedelta(days=7)
            qa_logs = db.query(QALog).filter(
                QALog.user_id == user_id,
                QALog.course_id == course_id,
                QALog.created_at >= seven_days_ago
            ).all()
            
            # 统计知识点出现次数和平均置信度
            kp_stats = {}
            for qa_log in qa_logs:
                kps = self._extract_knowledge_points_from_question(qa_log.question)
                for kp in kps:
                    if kp not in kp_stats:
                        kp_stats[kp] = {"count": 0, "total_confidence": 0}
                    kp_stats[kp]["count"] += 1
                    kp_stats[kp]["total_confidence"] += qa_log.confidence
            
            # 检查重复且低置信度的知识点
            repeat_count = 0
            for kp, stats in kp_stats.items():
                if (stats["count"] >= self.risk_thresholds["repeat_question_count"] and
                    stats["total_confidence"] / stats["count"] < self.risk_thresholds["low_confidence_threshold"]):
                    repeat_count += 1
            
            return repeat_count
            
        except Exception as e:
            logger.error(f"检查重复问题失败: {e}")
            return 0
    
    def _generate_suggestions(
        self,
        risk_level: str,
        weak_kp: List[WeakKnowledgePoint],
        active_7d: int
    ) -> List[str]:
        """生成学习建议"""
        suggestions = []
        
        if risk_level == "high":
            suggestions.append("建议立即制定学习计划，加强学习")
            suggestions.append("联系老师获得个性化指导")
        elif risk_level == "medium":
            suggestions.append("需要增加学习时间和频率")
            suggestions.append("重点关注薄弱知识点")
        
        if active_7d < 3:
            suggestions.append("建议每天至少学习30分钟")
        
        if weak_kp:
            top_weak = weak_kp[0].kp
            suggestions.append(f"重点复习{top_weak}相关内容")
        
        if not suggestions:
            suggestions.append("保持当前学习状态，继续努力")
        
        return suggestions[:3]  # 最多返回3个建议
    
    async def _get_weak_kp_distribution(
        self,
        db: Session,
        course_id: int
    ) -> List[WeakKPDistribution]:
        """获取班级薄弱知识点分布"""
        try:
            # 获取所有学生的问答记录
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            qa_logs = db.query(QALog).filter(
                QALog.course_id == course_id,
                QALog.created_at >= thirty_days_ago,
                QALog.confidence < 0.7  # 只统计低置信度的问答
            ).all()
            
            # 统计知识点出现次数
            kp_count = {}
            for qa_log in qa_logs:
                kps = self._extract_knowledge_points_from_question(qa_log.question)
                for kp in kps:
                    kp_count[kp] = kp_count.get(kp, 0) + 1
            
            # 转换为响应格式并排序
            distribution = [
                WeakKPDistribution(kp=kp, count=count)
                for kp, count in kp_count.items()
            ]
            distribution.sort(key=lambda x: x.count, reverse=True)
            
            return distribution[:10]  # 返回前10个
            
        except Exception as e:
            logger.error(f"获取薄弱知识点分布失败: {e}")
            return []
    
    async def _get_class_alerts(
        self,
        db: Session,
        course_id: int
    ) -> List[ClassAlert]:
        """获取班级预警"""
        try:
            # 获取所有学生
            students = db.query(User).filter(User.role == "student").all()
            
            alerts = []
            for student in students:
                # 获取学生画像
                profile = await self.get_student_profile(db, student.id, course_id)
                
                if profile.risk_level in ["medium", "high"]:
                    reason = "; ".join(profile.reasons) if profile.reasons else "学习状态需要关注"
                    alerts.append(ClassAlert(
                        user_id=student.id,
                        level=profile.risk_level,
                        reason=reason
                    ))
            
            # 按风险等级排序
            risk_order = {"high": 3, "medium": 2, "low": 1}
            alerts.sort(key=lambda x: risk_order.get(x.level, 0), reverse=True)
            
            return alerts
            
        except Exception as e:
            logger.error(f"获取班级预警失败: {e}")
            return []


# 全局服务实例
analytics_service = AnalyticsService()