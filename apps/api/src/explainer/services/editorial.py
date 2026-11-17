"""Publication policy shared by native, compatibility and saved-storyboard paths."""

import re
from ..editorial import CoverSpec
from ..content_taxonomy import INTENT_PROFILES


class EditorialError(ValueError):
    pass


EDITORIAL_INSTRUCTION = (
    "Create a publishable audience-focused video. Honor brief.editorial.intent, secondary_intents, subject_kind, "
    "audience_description, audience_level and presentation_forms as independent dimensions. "
    "Resolve one of introduction/explanation/analysis/viewpoint/advice/tutorial in editorial.strategy; "
    "knowledge is a subject, not a primary purpose. Resolve auto from semantic context with rationale, "
    "never keyword matching. Map an ordered narrative outline to every actual scene exactly once; "
    "include purpose-specific success criteria and preserve the requested secondary purposes. Honor "
    "core_message and viewer_takeaway. Establish one central question/message, evidence-backed "
    "supporting points, a concrete example where useful, and a conclusion/advice serving the viewer. "
    "Choose a narrative appropriate to a viewpoint, advice, project analysis, knowledge or mechanism; "
    "do not turn every project into a directory tour or feature list. For creator presentation return "
    "an editorial plan, give the first/last scenes opening/closing roles, and connect each scene's "
    "message/viewer_question to the central message. The cover must promise what the body delivers. "
    "Core opening text must be readable on frame zero, with immediate narration and no silent logo bumper. "
    "Use brief.creator_brand only if nonempty. Keep tool credits, provider configuration and execution "
    "diagnostics in reports, not narration or closing cards. Do not add EXPLAINER STUDIO/EVA headings "
    "or constant concept/static verification labels. Use short, timed disclosures only where necessary "
    "to interpret code examples or sample provenance. Never present another TTS provider's narration "
    "as a sample of the subject model, or imply a benchmark/listening test that was not performed. "
    "Keep claim/evidence IDs; inferred advice is not a measured result."
)


def prepare_presentation(board, brief, editorial=None):
    """Attach explicit presentation data without changing narration or measured timing.

    Historic storyboards remain loadable; only new native creator plans require EditorialPlan.
    Existing cover/editorial data are authoritative when editing a saved storyboard.
    """
    board.presentation_profile = brief.presentation_profile
    board.creator_brand = brief.creator_brand
    board.accent = brief.accent
    board.editorial_request = brief.editorial.model_copy(deep=True)
    if editorial is not None:
        board.editorial = editorial
    if board.presentation_profile == "creator":
        if board.cover is None:
            board.cover = (
                board.editorial.cover.model_copy() if board.editorial else CoverSpec(headline=board.title)
            )
        if len(board.scenes) > 1:
            if board.scenes[0].role == "content":
                board.scenes[0].role = "opening"
            if board.scenes[-1].role == "content":
                board.scenes[-1].role = "closing"
    return board


def publication_findings(board, content):
    """Deterministic failures plus warnings; semantic quality still needs image/content review."""
    findings = []

    def add(code, message, scene_id=None, severity="error"):
        findings.append(dict(code=code, severity=severity, message=message, scene_id=scene_id))

    if board.editorial:
        claims, evidence = {c.id for c in content.claims}, {e.id for e in content.evidence}
        for point in board.editorial.supports:
            if set(point.claim_ids) - claims or set(point.evidence_ids) - evidence:
                add("EDITORIAL_EVIDENCE", "内容主张引用不存在的证据")
            if content.kind == "source" and not (point.claim_ids or point.evidence_ids):
                add("EDITORIAL_EVIDENCE", "项目分析的支撑点需要关联提供的源码或文档依据")
        strategy = board.editorial.strategy
        if strategy:
            for finding in strategy_findings(board):
                findings.append(finding)
    if board.presentation_profile != "creator":
        return findings
    if not board.cover:
        add("MISSING_COVER", "创作者成片需要独立封面设计")
    if len(board.scenes) < 2 or board.scenes[0].role != "opening" or board.scenes[-1].role != "closing":
        add("MISSING_BOOKENDS", "创作者成片需要明确的开场与结尾场景")
    if board.editorial is None:
        add("EDITORIAL_REVIEW", "当前分镜尚无结构化内容策划；请核对主张与观众收益", severity="warning")
    elif board.editorial.strategy is None:
        add(
            "STRATEGY_REVIEW",
            "历史策划尚未解析四个内容维度；未自动认定为六类内容策划验收",
            severity="warning",
        )
    # The product name is valid when it is the actual subject; avoid a global banned-word list.
    tool_subject = re.search(
        r"engineering[ _-]*video[ _-]*agent|工程视频智能体|explainer studio", board.title, re.I
    )
    credits = re.compile(
        r"本片由.{0,100}(?:工程视频智能体|engineering video agent|explainer studio)"
        r"|(?:本片|本视频).{0,30}模板兼容模式|(?:made|produced|generated) (?:with|by) (?:engineering video agent|explainer studio)",
        re.I,
    )
    if not tool_subject:
        extra = []
        if board.cover:
            extra.extend([board.cover.headline, board.cover.subtitle])
        if board.editorial:
            extra.extend(
                [board.editorial.core_message, board.editorial.viewer_takeaway, board.editorial.closing]
            )
        if credits.search("\n".join(extra)):
            add("TOOL_SELF_CREDIT", "封面或内容主线包含无关的制作工具自宣传，请移入制作报告")
        for scene in board.scenes:
            text = "\n".join(
                [
                    scene.title,
                    scene.subtitle,
                    scene.narration,
                    scene.message,
                    *scene.bullets,
                    *(d.text for d in scene.disclosures),
                ]
            )
            if credits.search(text):
                add("TOOL_SELF_CREDIT", "观众内容包含无关的制作工具自宣传，请移入制作报告", scene.id)
    for scene in board.scenes:
        if any(
            d.text
            in {
                "概念讲解",
                "源码静态观察",
                "用户提供内容",
                "模板兼容模式",
                "CONCEPT",
                "SOURCE EVIDENCE",
                "USER BRIEF",
            }
            for d in scene.disclosures
        ):
            add("INTERNAL_VIEWER_LABEL", "内部验证分类不能作为创作者镜头的观众标签", scene.id)
    if sum(s.type.value == "cards" for s in board.scenes) > len(board.scenes) / 2:
        add("CARD_HEAVY", "要点卡片较多，建议用案例、关系和变化辅助表达", severity="warning")
    return findings


def strategy_findings(board):
    """Check explicit user constraints and structural coverage, not semantic truth."""
    strategy = board.editorial.strategy
    request = board.editorial_request
    findings = []

    def error(code, message):
        findings.append(dict(code=code, severity="error", message=message, scene_id=None))

    if request.intent != "auto" and strategy.intent != request.intent:
        error("INTENT_MISMATCH", "策划改变了用户明确选择的主要表达目的")
    if request.subject_kind != "auto" and strategy.subject_kind != request.subject_kind:
        error("SUBJECT_MISMATCH", "策划改变了用户明确选择的讲述对象")
    if set(request.secondary_intents) != set(strategy.secondary_intents):
        error("SECONDARY_MISMATCH", "辅助目的应保持用户选择，不能替代主要目的")
    if request.audience_level != "auto" and strategy.audience_level != request.audience_level:
        error("AUDIENCE_MISMATCH", "策划改变了用户明确选择的讲述深度")
    if not set(request.presentation_forms).issubset(strategy.presentation_forms):
        error("FORM_MISMATCH", "策划未覆盖用户选择的表现形式")
    covered = [scene_id for beat in strategy.outline for scene_id in beat.scene_ids]
    if covered != [s.id for s in board.scenes]:
        error("OUTLINE_COVERAGE", "叙事结构必须按顺序覆盖每个实际场景一次")
    profile = INTENT_PROFILES[strategy.intent]
    functions = {beat.function for beat in strategy.outline}
    if not set(profile["required"]).issubset(functions) or (
        profile["one_of"] and not functions.intersection(profile["one_of"])
    ):
        error("INTENT_STRUCTURE", "叙事缺少所选表达目的需要的论证、决策、解释或完成检查环节")
    if strategy.outline[-1].function != "conclusion":
        error("MISSING_CONCLUSION", "叙事结构需要以观众获得的结论或行动收束")
    return findings


def register_runtime_scene(board, scene_id):
    """Keep an existing argument beat aligned with an actually inserted runtime scene.

    Attaches observation to the preceding point; never invents an editorial purpose
    or a successful experiment. Repeated recovery insertion is idempotent.
    """
    if not board.editorial or not board.editorial.strategy:
        return
    outline = board.editorial.strategy.outline
    for beat in outline:
        beat.scene_ids = [i for i in beat.scene_ids if i != scene_id]
    outline[:] = [b for b in outline if b.scene_ids]
    index = next(i for i, s in enumerate(board.scenes) if s.id == scene_id)
    prior = board.scenes[index - 1].id
    for beat in outline:
        if prior in beat.scene_ids:
            beat.scene_ids.insert(beat.scene_ids.index(prior) + 1, scene_id)
            return


def require_publishable(board, content):
    errors = [f for f in publication_findings(board, content) if f["severity"] == "error"]
    if errors:
        raise EditorialError("；".join(f["message"] for f in errors))
