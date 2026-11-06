"""Local AI assistant — heuristic suggestions (no cloud required)."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.modules.reports.services.report_service import ReportService
from app.modules.work_orders.repositories.work_order_repository import WorkOrderRepository


@dataclass(frozen=True, slots=True)
class AiSuggestion:
    title: str
    detail: str
    route: str | None = None


@dataclass(frozen=True, slots=True)
class AiReply:
    text: str
    suggestions: list[AiSuggestion]


class AiAssistantService:
    """
    On-device operator assistant.

    Uses live KPIs and simple keyword matching. External LLM can be
    plugged later via settings without changing this contract.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def suggestions(self, company_id: int) -> list[AiSuggestion]:
        stats = ReportService(self._session).dashboard_stats(company_id)
        items: list[AiSuggestion] = []
        if stats.approval_waiting:
            items.append(
                AiSuggestion(
                    title="Narx tasdiqi kutilyapti",
                    detail=f"{stats.approval_waiting} ta buyurtma mijoz roziligini kutmoqda.",
                    route="work_orders",
                )
            )
        if stats.ready_count:
            items.append(
                AiSuggestion(
                    title="Olib ketishga tayyor",
                    detail=f"{stats.ready_count} ta qurilma tayyor — mijozni xabardor qiling.",
                    route="work_orders",
                )
            )
        if stats.low_stock_items:
            items.append(
                AiSuggestion(
                    title="Kam zaxira",
                    detail=f"{stats.low_stock_items} ta mahsulot minimal zaxiradan past.",
                    route="inventory",
                )
            )
        if stats.waiting_count:
            items.append(
                AiSuggestion(
                    title="Jarayondagi ishlar",
                    detail=f"{stats.waiting_count} ta buyurtma hali yopilmagan.",
                    route="work_orders",
                )
            )
        if not items:
            items.append(
                AiSuggestion(
                    title="Hammasi joyida",
                    detail="Kritik ogohlantirish yoʻq. Tezkor qabul yoki hisobotlarni oching.",
                    route="reception",
                )
            )
        return items

    def ask(self, company_id: int, question: str) -> AiReply:
        q = (question or "").strip().lower()
        if not q:
            return AiReply(
                text="Savol yozing — masalan: «tayyor buyurtmalar», «kam zaxira», «bugungi daromad».",
                suggestions=self.suggestions(company_id),
            )
        stats = ReportService(self._session).dashboard_stats(company_id)
        if any(w in q for w in ("tayyor", "ready", "olib")):
            text = f"Hozir {stats.ready_count} ta buyurtma olib ketishga tayyor."
            return AiReply(text=text, suggestions=self.suggestions(company_id))
        if any(w in q for w in ("zaxira", "ombor", "stock")):
            text = f"Kam zaxira: {stats.low_stock_items} ta mahsulot."
            return AiReply(text=text, suggestions=self.suggestions(company_id))
        if any(w in q for w in ("daromad", "pul", "revenue", "tushum")):
            text = (
                f"Bugungi daromad: {stats.revenue_today:,} soʻm; "
                f"xarajat: {stats.expense_today:,} soʻm."
            ).replace(",", " ")
            return AiReply(text=text, suggestions=self.suggestions(company_id))
        if any(w in q for w in ("tasdiq", "narx", "rozilik", "approve")):
            text = f"Narx tasdiqini kutayotganlar: {stats.approval_waiting}."
            return AiReply(text=text, suggestions=self.suggestions(company_id))
        if any(w in q for w in ("qabul", "bugun", "reception")):
            text = f"Bugun qabul qilingan: {stats.today_received}; topshirildi: {stats.completed_today}."
            return AiReply(text=text, suggestions=self.suggestions(company_id))
        if "wo-" in q or "buyurtma" in q:
            repo = WorkOrderRepository(self._session)
            rows = repo.search(company_id, query=q.replace("buyurtma", "").strip(), limit=5)
            if not rows:
                text = "Mos buyurtma topilmadi. Toʻliq raqam bilan qidiring (WO-000001)."
            else:
                parts = [
                    f"{o.number}: {o.status}"
                    for o in rows
                ]
                text = "Topilganlar:\n" + "\n".join(parts)
            return AiReply(text=text, suggestions=self.suggestions(company_id))
        return AiReply(
            text=(
                "Mahalliy yordamchi tushundi: umumiy savol. "
                f"KPI: bugun qabul {stats.today_received}, tayyor {stats.ready_count}, kam zaxira {stats.low_stock_items}."
            ),
            suggestions=self.suggestions(company_id),
        )
