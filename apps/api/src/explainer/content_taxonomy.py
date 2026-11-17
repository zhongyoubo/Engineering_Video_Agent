"""Versioned editorial vocabulary and guidance, never a keyword intent router."""

from copy import deepcopy
from typing import Literal

ContentIntent = Literal["introduction", "explanation", "analysis", "viewpoint", "advice", "tutorial"]
RequestedIntent = Literal[
    "auto", "introduction", "explanation", "analysis", "viewpoint", "advice", "tutorial"
]
ContentSubject = Literal[
    "project",
    "product",
    "technology",
    "knowledge",
    "concept",
    "mechanism",
    "method",
    "workflow",
    "problem",
    "phenomenon",
]
RequestedSubject = Literal[
    "auto",
    "project",
    "product",
    "technology",
    "knowledge",
    "concept",
    "mechanism",
    "method",
    "workflow",
    "problem",
    "phenomenon",
]
PresentationForm = Literal[
    "diagram", "case_study", "comparison", "demonstration", "code_walkthrough", "data_visualization", "story"
]
AudienceLevel = Literal["introductory", "intermediate", "advanced"]
BeatFunction = Literal[
    "orientation",
    "definition",
    "mechanism",
    "evidence",
    "comparison",
    "counterargument",
    "limitations",
    "decision",
    "steps",
    "example",
    "application",
    "check",
    "conclusion",
]

INTENT_PROFILES = {
    "introduction": {
        "label": "介绍告知",
        "entry_label": "介绍一个事物",
        "question": "它是什么，有哪些值得知道的信息？",
        "arc": ["orientation", "evidence", "application", "conclusion"],
        "required": ["orientation"],
        "one_of": [],
        "success_criteria": ["观众能说清对象与核心信息", "事实有来源，重点有取舍"],
        "evidence_guidance": "Distinguish documented facts from observed results; do not read a complete feature list.",
    },
    "explanation": {
        "label": "解释理解",
        "entry_label": "讲懂一个道理",
        "question": "这是什么，为什么会这样，如何运作？",
        "arc": ["orientation", "definition", "mechanism", "example", "conclusion"],
        "required": [],
        "one_of": ["definition", "mechanism"],
        "success_criteria": ["观众能解释核心对象、关系或变化", "至少一个具体情境帮助理解，类比说明适用边界"],
        "evidence_guidance": "Use evidence-backed relationships; do not mistake file organization for a runtime mechanism.",
    },
    "analysis": {
        "label": "分析评估",
        "entry_label": "分析一个对象",
        "question": "设计怎样，价值与取舍是什么，适合什么条件？",
        "arc": ["orientation", "evidence", "comparison", "limitations", "conclusion"],
        "required": [],
        "one_of": ["evidence", "comparison"],
        "success_criteria": ["有明确的分析维度与依据", "结论说明价值、取舍与适用边界"],
        "evidence_guidance": "Separate static analysis, inference and runtime measurement. Comparisons must identify their basis.",
    },
    "viewpoint": {
        "label": "观点论证",
        "entry_label": "表达一个观点",
        "question": "我的判断是什么，为什么值得相信？",
        "arc": ["orientation", "evidence", "counterargument", "conclusion"],
        "required": ["evidence"],
        "one_of": ["counterargument", "limitations"],
        "success_criteria": ["中心判断明确，理由与证据支持它", "回应其他解释或适用边界，避免只有立场"],
        "evidence_guidance": "A viewpoint is an argument, not a measured fact. Show support and qualify its scope.",
    },
    "advice": {
        "label": "建议决策",
        "entry_label": "给出一个建议",
        "question": "在什么条件下，应该怎样选择或行动？",
        "arc": ["orientation", "evidence", "decision", "application", "conclusion"],
        "required": ["decision"],
        "one_of": ["steps", "application"],
        "success_criteria": ["建议与具体需求、条件相连", "观众知道下一步可以做什么"],
        "evidence_guidance": "Give conditional advice grounded in supplied evidence; do not invent product tests or endorsements.",
    },
    "tutorial": {
        "label": "教学操作",
        "entry_label": "教会一种做法",
        "question": "需要什么，怎样完成，如何判断是否成功？",
        "arc": ["orientation", "steps", "example", "check", "conclusion"],
        "required": ["steps", "check"],
        "one_of": [],
        "success_criteria": ["前提、关键步骤与预期结果清楚", "提供完成判断方法，示意与实际操作明确区分"],
        "evidence_guidance": "Describe reproducible steps and a completion check. Never imply an unexecuted example actually ran.",
    },
}
SUBJECTS = {
    "project": "项目",
    "product": "产品",
    "technology": "技术",
    "knowledge": "知识点",
    "concept": "概念",
    "mechanism": "原理与机制",
    "method": "方法",
    "workflow": "流程",
    "problem": "问题",
    "phenomenon": "现象",
}
FORMS = {
    "diagram": "图解动画",
    "case_study": "案例讲解",
    "comparison": "对比分析",
    "demonstration": "实操演示",
    "code_walkthrough": "代码讲解",
    "data_visualization": "数据展示",
    "story": "故事叙述",
}
LEVELS = {"introductory": "入门", "intermediate": "进阶", "advanced": "深入"}


def taxonomy_options():
    return deepcopy(
        {
            "version": "1.0",
            "intents": [{"id": k, **v} for k, v in INTENT_PROFILES.items()],
            "subjects": [{"id": k, "label": v} for k, v in SUBJECTS.items()],
            "presentation_forms": [{"id": k, "label": v} for k, v in FORMS.items()],
            "audience_levels": [{"id": k, "label": v} for k, v in LEVELS.items()],
        }
    )


def planning_guidance(brief):
    """Honor explicit purposes. Only a model may resolve auto from semantic context."""
    selected = brief.editorial.intent
    return {
        "taxonomy_version": "1.0",
        "request": brief.editorial.model_dump(),
        "audience_category": brief.audience,
        "profiles": deepcopy(
            INTENT_PROFILES if selected == "auto" else {selected: INTENT_PROFILES[selected]}
        ),
        "resolution": "Use the full audience/question/material context. Resolve auto in editorial.strategy with rationale; no keyword routing. Select one primary purpose, optional secondary purposes, a separate subject, audience depth and presentation forms. Suggested arcs are guidance, not fixed scene templates. Map the chosen outline to actual ordered scene IDs. Knowledge is a subject/field, not a primary purpose.",
    }
