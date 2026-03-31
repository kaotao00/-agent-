from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from tender_system.llm import SectionWriter
from tender_system.retrieval import Retriever
from tender_system.schemas import TenderRequest


@dataclass
class SharedMemory:
    facts: dict[str, Any] = field(default_factory=dict)
    logs: list[str] = field(default_factory=list)

    def update(self, key: str, value: Any) -> None:
        self.facts[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self.facts.get(key, default)

    def log(self, message: str) -> None:
        self.logs.append(message)


@dataclass
class AgentContext:
    request: TenderRequest
    retriever: Retriever
    memory: SharedMemory
    writer: SectionWriter


def _format_hits_for_prompt(hits: list[Any]) -> str:
    if not hits:
        return "无"
    return "\n".join(f"- {hit.title}: {hit.excerpt}" for hit in hits)


class MockPricingTool:
    def __init__(self) -> None:
        self.rate_card = {
            "A101": {"name": "土方开挖", "unit_price": 38.0},
            "B205": {"name": "钢筋工程", "unit_price": 4680.0},
            "C310": {"name": "混凝土浇筑", "unit_price": 520.0},
            "D410": {"name": "脚手架搭设", "unit_price": 62.0},
        }

    def price_items(self, boq: list[dict[str, Any]]) -> dict[str, Any]:
        priced_items: list[dict[str, Any]] = []
        total = 0.0
        for item in boq:
            rate = self.rate_card.get(item["item_code"], {"unit_price": 100.0})
            subtotal = round(item["quantity"] * rate["unit_price"], 2)
            total += subtotal
            priced_items.append(
                {
                    "item_code": item["item_code"],
                    "item_name": item["item_name"],
                    "quantity": item["quantity"],
                    "unit": item["unit"],
                    "unit_price": rate["unit_price"],
                    "subtotal": subtotal,
                }
            )
        return {"priced_items": priced_items, "total_quote": round(total, 2)}


class ProjectManagerAgent:
    def plan(self, context: AgentContext) -> dict[str, Any]:
        req = context.request
        context.memory.update("project_name", req.project_name)
        context.memory.update("project_type", req.project_type)
        context.memory.update("region", req.region)
        context.memory.update("duration_days", req.tender_requirements.duration_days)
        context.memory.update("quality_target", req.tender_requirements.quality_target)
        context.memory.update("safety_target", req.tender_requirements.safety_target)
        context.memory.update("required_qualification", req.tender_requirements.required_qualification)
        context.memory.log("ProjectManagerAgent parsed the tender request and initialized shared memory.")
        return {
            "tasks": [
                "解析招标要求",
                "生成技术方案",
                "生成预算报价",
                "组装商务资质",
                "执行合规校验",
            ],
            "execution_order": ["technical", "budget", "business", "compliance"],
            "coordination_strategy": "先拆解需求，再由领域 Agent 并行生成，最后统一做规则审查与一致性回写。",
        }


class TechnicalProposalAgent:
    def generate(self, context: AgentContext) -> dict[str, Any]:
        req = context.request
        hits = context.retriever.search(
            query=f"{req.project_type} {req.region} 施工组织 质量 安全 工期",
            top_k=3,
            filters={"project_type": req.project_type, "region": req.region, "category": "technical"},
        )
        duration = context.memory.get("duration_days")
        quality_target = context.memory.get("quality_target")
        safety_target = context.memory.get("safety_target")
        generated = context.writer.generate_json(
            system_prompt=(
                "你是建筑工程投标中的技术方案Agent。必须基于给定事实生成严谨、专业、可落地的技术方案。"
                "只输出JSON对象，字段必须包含 construction_method, schedule_plan, resource_plan, quality_and_safety, innovation_points。"
            ),
            user_prompt=(
                f"项目名称: {req.project_name}\n"
                f"项目类型: {req.project_type}\n"
                f"地区: {req.region}\n"
                f"工期: {duration}天\n"
                f"质量目标: {quality_target}\n"
                f"安全目标: {safety_target}\n"
                f"可参考知识:\n{_format_hits_for_prompt(hits)}\n"
                "要求: 方案贴合工业建筑总承包场景，内容专业，不虚构具体规范编号。"
            ),
        )
        context.memory.update("technical_duration_days", duration)
        context.memory.log("TechnicalProposalAgent completed technical proposal drafting.")
        payload = {
            "section": "技术方案",
            "construction_method": "采用分区流水施工与穿插作业模式，基础、主体、机电安装按里程碑倒排推进，关键工序执行样板先行。",
            "schedule_plan": f"总工期控制在 {duration} 天，前 30 天完成基础工程，120 天内实现主体结构封顶，后续完成安装与装饰联动收尾。",
            "resource_plan": "项目部配置项目经理、技术负责人、安全总监、质量负责人及专业班组，周维度滚动编排材料、机械与劳务资源。",
            "quality_and_safety": f"质量目标：{quality_target}；安全目标：{safety_target}；执行三级安全教育、专项方案审批、样板验收和质量闭环整改。",
            "innovation_points": "引入 BIM 深化与工序样板交底机制，提升复杂节点预控能力。",
            "rag_references": [hit.title for hit in hits],
        }
        if generated:
            payload.update({key: value for key, value in generated.items() if key in payload and key != "section"})
            payload["generation_mode"] = context.writer.backend_name
        else:
            payload["generation_mode"] = "template"
        return payload


class BudgetQuotationAgent:
    def __init__(self) -> None:
        self.pricing_tool = MockPricingTool()

    def generate(self, context: AgentContext) -> dict[str, Any]:
        req = context.request
        hits = context.retriever.search(
            query=f"{req.project_type} {req.region} 预算 报价 定额 计价",
            top_k=3,
            filters={"project_type": req.project_type, "region": req.region, "category": "budget"},
        )
        pricing_result = self.pricing_tool.price_items([item.model_dump() for item in req.bill_of_quantities])
        base_cost = pricing_result["total_quote"]
        management_fee = round(base_cost * 0.05, 2)
        measure_fee = round(base_cost * 0.03, 2)
        tax = round((base_cost + management_fee + measure_fee) * 0.09, 2)
        bid_total = round(base_cost + management_fee + measure_fee + tax, 2)
        generated = context.writer.generate_json(
            system_prompt=(
                "你是建筑工程投标中的预算报价Agent。必须输出JSON对象，字段必须包含 pricing_basis, cost_analysis, quotation_strategy。"
                "不要修改已给定的金额，只负责生成解释性文本。"
            ),
            user_prompt=(
                f"项目名称: {req.project_name}\n"
                f"地区: {req.region}\n"
                f"项目类型: {req.project_type}\n"
                f"基础成本: {base_cost}\n"
                f"管理费: {management_fee}\n"
                f"措施费: {measure_fee}\n"
                f"税金: {tax}\n"
                f"总报价: {bid_total}\n"
                f"清单项数量: {len(req.bill_of_quantities)}\n"
                f"可参考知识:\n{_format_hits_for_prompt(hits)}\n"
                "要求: 说明报价依据、成本构成和报价策略，适合标书表达。"
            ),
        )
        context.memory.update("quoted_total", bid_total)
        context.memory.log("BudgetQuotationAgent called the pricing tool and generated the budget section.")
        payload = {
            "section": "预算报价",
            "priced_items": pricing_result["priced_items"],
            "base_cost": base_cost,
            "management_fee": management_fee,
            "measure_fee": measure_fee,
            "tax": tax,
            "bid_total": bid_total,
            "pricing_basis": "结合企业定额计价系统、地区价格经验库和工程量清单自动生成报价测算结果。",
            "cost_analysis": "以清单工程量为基础，叠加管理费、措施费和税金形成完整投标报价口径。",
            "quotation_strategy": "在满足招标要求和企业利润目标前提下，结合历史中标区间保持报价竞争力。",
            "rag_references": [hit.title for hit in hits],
        }
        if generated:
            payload.update({key: value for key, value in generated.items() if key in payload})
            payload["generation_mode"] = context.writer.backend_name
        else:
            payload["generation_mode"] = "template"
        return payload


class BusinessQualificationAgent:
    def generate(self, context: AgentContext) -> dict[str, Any]:
        req = context.request
        hits = context.retriever.search(
            query=f"{req.region} 资质 业绩 项目经理 证书",
            top_k=3,
            filters={"region": req.region, "category": "business"},
        )
        qualification = context.memory.get("required_qualification")
        generated = context.writer.generate_json(
            system_prompt=(
                "你是建筑工程投标中的商务资质Agent。必须输出JSON对象，字段必须包含 commitment, credential_summary, team_statement。"
                "内容要正式、商务化，不能虚构新的资质等级。"
            ),
            user_prompt=(
                f"项目名称: {req.project_name}\n"
                f"地区: {req.region}\n"
                f"要求资质: {qualification}\n"
                f"可参考知识:\n{_format_hits_for_prompt(hits)}\n"
                "要求: 输出适合投标文件的商务响应说明。"
            ),
        )
        context.memory.update("business_qualification", qualification)
        context.memory.log("BusinessQualificationAgent assembled business qualifications and enterprise credentials.")
        payload = {
            "section": "商务资质",
            "enterprise_qualification": qualification,
            "project_manager": {
                "name": "张明",
                "certificate": "一级建造师（建筑工程）",
                "experience": "主持过 3 个大型工业园区总承包项目。",
            },
            "similar_projects": [
                "苏州智能制造基地厂房工程",
                "南京高端装备产业园 EPC 项目",
                "无锡先进材料研发中心土建工程",
            ],
            "commitment": "承诺按招标文件要求提供完整商务响应资料，确保资质、业绩、项目经理证书和授权材料可核验。",
            "credential_summary": "企业具备建筑工程施工总承包一级资质，具备工业厂房与园区类项目实施经验。",
            "team_statement": "拟派项目团队具备类似工程履约经验，能够满足本项目履约和管理要求。",
            "rag_references": [hit.title for hit in hits],
        }
        if generated:
            payload.update({key: value for key, value in generated.items() if key in payload})
            payload["generation_mode"] = context.writer.backend_name
        else:
            payload["generation_mode"] = "template"
        return payload


class ComplianceReviewAgent:
    def validate(self, context: AgentContext, sections: dict[str, dict[str, Any]]) -> dict[str, Any]:
        req = context.request.tender_requirements
        issues: list[str] = []
        if sections["business"]["enterprise_qualification"] != req.required_qualification:
            issues.append("企业资质与招标要求不一致")
        if context.memory.get("technical_duration_days") != req.duration_days:
            issues.append("技术方案工期与招标要求不一致")
        if sections["budget"]["bid_total"] <= 0:
            issues.append("预算总价异常")
        if set(req.bid_sections) - (set(sections.keys()) | {"compliance"}):
            issues.append("存在未生成的标书模块")
        if context.memory.get("quoted_total") != sections["budget"]["bid_total"]:
            issues.append("共享记忆中的报价金额与预算模块不一致")
        verdict = "pass" if not issues else "fail"
        context.memory.log(f"ComplianceReviewAgent finished validation with verdict={verdict}.")
        return {
            "section": "合规校验",
            "verdict": verdict,
            "issues": issues,
            "checked_rules": ["工期一致性", "资质一致性", "报价有效性", "共享记忆一致性", "标书模块完整性"],
        }
