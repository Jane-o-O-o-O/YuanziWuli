import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.orm import QALog, Event, KnowledgePoint, KPRelation
from app.models.schemas import RecommendationResponse, RecommendationItem, ProfileRecommendationResponse, LearningPlan
from app.services.llm_client import llm_client, ChatMessage

logger = logging.getLogger(__name__)


class RecommendationService:
    """推荐服务"""
    
    def __init__(self):
        # 原子物理学知识点映射
        self.knowledge_points = {
            "原子结构": {
                "prerequisites": ["经典物理学基础", "电磁学基础"],
                "examples": ["氢原子模型", "多电子原子"],
                "pitfalls": ["混淆轨道和能级概念", "忽略电子间相互作用"],
                "next_steps": ["量子数", "电子排布"]
            },
            "波粒二象性": {
                "prerequisites": ["光的波动性", "粒子性质"],
                "examples": ["双缝实验", "光电效应", "康普顿散射"],
                "pitfalls": ["认为光只有波动性或粒子性", "混淆经典和量子概念"],
                "next_steps": ["不确定性原理", "物质波"]
            },
            "量子数": {
                "prerequisites": ["原子结构", "角动量"],
                "examples": ["主量子数n", "角量子数l", "磁量子数m", "自旋量子数s"],
                "pitfalls": ["量子数取值范围错误", "混淆不同量子数的物理意义"],
                "next_steps": ["电子排布", "泡利不相容原理"]
            },
            "原子光谱": {
                "prerequisites": ["原子结构", "能级跃迁"],
                "examples": ["氢原子光谱", "巴尔末系", "莱曼系"],
                "pitfalls": ["混淆发射和吸收光谱", "计算波长时单位错误"],
                "next_steps": ["精细结构", "塞曼效应"]
            },
            "电子自旋": {
                "prerequisites": ["量子数", "角动量"],
                "examples": ["斯特恩-格拉赫实验", "自旋轨道耦合"],
                "pitfalls": ["认为自旋是经典旋转", "忽略自旋磁矩"],
                "next_steps": ["泡利不相容原理", "原子磁性"]
            }
        }
    
    async def recommend_by_question(
        self,
        db: Session,
        course_id: int,
        question: str
    ) -> RecommendationResponse:
        """基于问题的推荐"""
        try:
            # 分析问题涉及的知识点
            knowledge_points = await self._analyze_question_knowledge_points(question)
            
            # 生成推荐内容
            recommendations = RecommendationResponse()
            
            for kp in knowledge_points:
                if kp in self.knowledge_points:
                    kp_info = self.knowledge_points[kp]
                    
                    # 前置知识
                    for prereq in kp_info["prerequisites"]:
                        recommendations.prerequisites.append(
                            RecommendationItem(
                                kp=prereq,
                                description=f"学习{kp}需要先掌握{prereq}",
                                actions=[f"复习{prereq}相关内容", f"做{prereq}练习题"]
                            )
                        )
                    
                    # 例题推荐
                    for example in kp_info["examples"]:
                        recommendations.examples.append(
                            RecommendationItem(
                                kp=example,
                                description=f"{kp}的典型例子",
                                actions=[f"学习{example}案例", f"练习{example}相关题目"]
                            )
                        )
                    
                    # 易错点
                    for pitfall in kp_info["pitfalls"]:
                        recommendations.pitfalls.append(
                            RecommendationItem(
                                kp=pitfall,
                                description=f"{kp}常见误区",
                                actions=["注意概念区分", "多做对比练习"]
                            )
                        )
                    
                    # 下一步学习
                    for next_step in kp_info["next_steps"]:
                        recommendations.next_steps.append(
                            RecommendationItem(
                                kp=next_step,
                                description=f"掌握{kp}后可以学习{next_step}",
                                actions=[f"开始学习{next_step}", f"查看{next_step}相关资料"]
                            )
                        )
            
            # 去重并限制数量
            recommendations.prerequisites = recommendations.prerequisites[:3]
            recommendations.examples = recommendations.examples[:3]
            recommendations.pitfalls = recommendations.pitfalls[:3]
            recommendations.next_steps = recommendations.next_steps[:3]
            
            return recommendations
            
        except Exception as e:
            logger.error(f"基于问题的推荐失败: {e}")
            return RecommendationResponse()
    
    async def recommend_by_profile(
        self,
        db: Session,
        user_id: int,
        course_id: int
    ) -> ProfileRecommendationResponse:
        """基于用户画像的推荐"""
        try:
            # 分析用户薄弱知识点
            weak_points = await self._analyze_weak_knowledge_points(db, user_id, course_id)
            
            # 生成学习计划
            learning_plan = []
            
            for weak_kp, score in weak_points:
                if weak_kp in self.knowledge_points:
                    kp_info = self.knowledge_points[weak_kp]
                    
                    actions = []
                    
                    # 根据薄弱程度确定学习策略
                    if score < 0.3:
                        # 非常薄弱，从基础开始
                        actions.extend([
                            f"重新学习{weak_kp}基础概念",
                            f"复习{weak_kp}的前置知识",
                            f"做{weak_kp}基础练习题"
                        ])
                    elif score < 0.6:
                        # 中等薄弱，加强练习
                        actions.extend([
                            f"加强{weak_kp}概念理解",
                            f"多做{weak_kp}应用题",
                            f"总结{weak_kp}易错点"
                        ])
                    else:
                        # 轻微薄弱，查漏补缺
                        actions.extend([
                            f"复习{weak_kp}重点内容",
                            f"做{weak_kp}综合题",
                            f"准备学习后续内容"
                        ])
                    
                    learning_plan.append(
                        LearningPlan(
                            kp=weak_kp,
                            actions=actions[:3]  # 限制每个知识点最多3个行动
                        )
                    )
            
            return ProfileRecommendationResponse(plan=learning_plan[:5])  # 最多5个知识点
            
        except Exception as e:
            logger.error(f"基于画像的推荐失败: {e}")
            return ProfileRecommendationResponse(plan=[])
    
    async def _analyze_question_knowledge_points(self, question: str) -> List[str]:
        """分析问题涉及的知识点"""
        try:
            # 使用LLM分析问题涉及的知识点
            prompt = f"""请分析以下原子物理学问题涉及的主要知识点，从以下列表中选择最相关的1-3个：

知识点列表：
- 原子结构
- 波粒二象性  
- 量子数
- 原子光谱
- 电子自旋
- 能级跃迁
- 不确定性原理
- 物质波
- 光电效应
- 康普顿散射

问题：{question}

请只返回知识点名称，用逗号分隔："""

            messages = [ChatMessage(role="user", content=prompt)]
            response = await llm_client.chat_completion(messages, temperature=0.1)
            
            # 解析响应
            knowledge_points = [kp.strip() for kp in response.content.split(',')]
            return [kp for kp in knowledge_points if kp in self.knowledge_points]
            
        except Exception as e:
            logger.warning(f"LLM分析知识点失败，使用关键词匹配: {e}")
            return self._keyword_match_knowledge_points(question)
    
    def _keyword_match_knowledge_points(self, question: str) -> List[str]:
        """基于关键词匹配知识点"""
        keywords_map = {
            "原子结构": ["原子", "结构", "模型", "核外电子", "轨道"],
            "波粒二象性": ["波粒二象性", "波动", "粒子", "双缝", "干涉"],
            "量子数": ["量子数", "主量子数", "角量子数", "磁量子数", "自旋量子数"],
            "原子光谱": ["光谱", "谱线", "巴尔末", "莱曼", "发射", "吸收"],
            "电子自旋": ["自旋", "斯特恩", "格拉赫", "磁矩"]
        }
        
        matched_kps = []
        for kp, keywords in keywords_map.items():
            if any(keyword in question for keyword in keywords):
                matched_kps.append(kp)
        
        return matched_kps[:3]  # 最多返回3个
    
    async def _analyze_weak_knowledge_points(
        self,
        db: Session,
        user_id: int,
        course_id: int
    ) -> List[tuple]:
        """分析用户薄弱知识点"""
        try:
            # 获取用户最近的问答记录
            recent_qa_logs = db.query(QALog).filter(
                QALog.user_id == user_id,
                QALog.course_id == course_id
            ).order_by(QALog.created_at.desc()).limit(20).all()
            
            # 统计知识点的置信度
            kp_confidence = {}
            kp_count = {}
            
            for qa_log in recent_qa_logs:
                # 简单的知识点提取（基于问题关键词）
                question_kps = self._keyword_match_knowledge_points(qa_log.question)
                
                for kp in question_kps:
                    if kp not in kp_confidence:
                        kp_confidence[kp] = 0
                        kp_count[kp] = 0
                    
                    kp_confidence[kp] += qa_log.confidence
                    kp_count[kp] += 1
            
            # 计算平均置信度并排序
            weak_points = []
            for kp in kp_confidence:
                if kp_count[kp] > 0:
                    avg_confidence = kp_confidence[kp] / kp_count[kp]
                    weak_points.append((kp, avg_confidence))
            
            # 按置信度升序排序（最薄弱的在前）
            weak_points.sort(key=lambda x: x[1])
            
            return weak_points[:5]  # 返回最薄弱的5个知识点
            
        except Exception as e:
            logger.error(f"分析薄弱知识点失败: {e}")
            return []


# 全局服务实例
rec_service = RecommendationService()