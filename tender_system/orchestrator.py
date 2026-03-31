from __future__ import annotations

from tender_system.agents import (
    AgentContext,
    BusinessQualificationAgent,
    ComplianceReviewAgent,
    BudgetQuotationAgent,
    ProjectManagerAgent,
    SharedMemory,
    TechnicalProposalAgent,
)
from tender_system.llm import SectionWriter
from tender_system.retrieval import Retriever
from tender_system.schemas import TenderGenerationResult, TenderRequest


class TenderOrchestrator:
    def __init__(self, retriever: Retriever, writer: SectionWriter) -> None:
        self.retriever = retriever
        self.writer = writer
        self.project_manager = ProjectManagerAgent()
        self.technical_agent = TechnicalProposalAgent()
        self.budget_agent = BudgetQuotationAgent()
        self.business_agent = BusinessQualificationAgent()
        self.compliance_agent = ComplianceReviewAgent()

    def run(self, tender_request: TenderRequest) -> TenderGenerationResult:
        memory = SharedMemory()
        context = AgentContext(request=tender_request, retriever=self.retriever, memory=memory, writer=self.writer)
        plan = self.project_manager.plan(context)
        sections = {
            "technical": self.technical_agent.generate(context),
            "budget": self.budget_agent.generate(context),
            "business": self.business_agent.generate(context),
        }
        sections["compliance"] = self.compliance_agent.validate(context, sections)
        return TenderGenerationResult(
            project_name=tender_request.project_name,
            execution_plan=plan,
            sections=sections,
            shared_memory=memory.facts,
            agent_logs=memory.logs,
            retrieval_backend=f"{self.retriever.backend_name}+{self.writer.backend_name}",
        )
