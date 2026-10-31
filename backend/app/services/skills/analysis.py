"""项目分析扩展点：后续模型适配器实现 ProjectAnalyzer，输出需经 ProjectAnalysis 校验。

README 为不可信输入；适配器仅分析文本，不执行其中指令或命令。
"""

import re
from typing import Literal, Protocol

from pydantic import BaseModel, Field

# 标签、识别证据、核心能力、适用场景、知识内容方向。规则命中仅代表资料提及。
CAPABILITIES = [
    (
        "视频生成",
        r"text.to.video|image.to.video|video.generat|文生视频|图生视频",
        "根据文本或图片生成视频",
        "知识科普短视频、概念演示与故事分镜",
        "科普知识、历史故事、创意故事",
    ),
    (
        "二维动画",
        r"2d.animation|cartoon|anime|二维动画|卡通|动漫",
        "二维角色或卡通动画制作",
        "卡通知识短片、故事动画",
        "儿童启蒙、趣味科普、故事讲解",
    ),
    (
        "三维动画",
        r"3d.animation|text.to.3d|image.to.3d|三维动画",
        "三维内容生成与动画制作",
        "立体结构演示与产品动画",
        "工程原理、产品结构、空间知识",
    ),
    (
        "动画",
        r"animation|motion.graphics|remotion|manim|动画|动效",
        "程序化动画与动态图形",
        "数学推导、数据可视化与文字动效短片",
        "数学、物理、数据科普",
    ),
    (
        "数字人",
        r"talking.head|lip.sync|avatar|数字人|口型同步",
        "数字人口播或口型同步",
        "口播知识视频与多语言讲解",
        "知识讲解、语言学习、课程导读",
    ),
    (
        "配音",
        r"text.to.speech|\btts\b|voiceover|voice.clon|配音|语音合成",
        "语音合成、旁白或声音克隆",
        "知识短视频旁白、有声故事与课程配音",
        "历史人文、故事、语言学习",
    ),
    (
        "字幕",
        r"subtitle|caption|transcri|\bsrt\b|\basr\b|字幕|转录",
        "语音转文字与字幕处理",
        "访谈、课程和知识短视频字幕",
        "访谈解读、课程笔记、外语学习",
    ),
    (
        "剪辑",
        r"video.edit|video.process|ffmpeg|剪辑|视频处理",
        "视频剪辑与素材处理",
        "知识短视频拼接、课程切片与格式转换",
        "教程、知识合集、课程精华",
    ),
    (
        "音乐音效",
        r"music.generat|text.to.audio|sound.effect|audio.generat|音乐生成|音效",
        "音乐或音效生成",
        "故事短片配乐与环境音效",
        "音乐知识、故事、沉浸式科普",
    ),
    (
        "脚本写作",
        r"scriptwriting|screenplay|copywriting|storytelling|脚本写作|文案|剧本",
        "文案与视频脚本辅助写作",
        "知识口播脚本、剧情分镜与内容提纲",
        "知识讲解、人物故事、观点解读",
    ),
    (
        "文档办公",
        r"document.ai|document.assistant|\bpdf\b|\bocr\b|文档|智能写作",
        "文档解析、识别或写作辅助",
        "资料整理、文献摘录与报告写作",
        "阅读笔记、研究资料、办公教程",
    ),
    (
        "表格数据",
        r"spreadsheet|excel|data.analysis|表格|数据分析",
        "表格处理与数据分析辅助",
        "数据清洗、统计报表与图表制作",
        "商业分析、数据科普、效率办公",
    ),
    (
        "演示文稿",
        r"presentation|powerpoint|\bpptx?\b|幻灯片|演示文稿",
        "演示文稿辅助生成",
        "知识课程课件、培训材料与汇报",
        "课程教学、职场技能、知识分享",
    ),
    (
        "会议助手",
        r"meeting.assistant|meeting.notes|meeting.transcri|会议纪要|会议助手",
        "会议转录与纪要整理",
        "会议记录、访谈摘要与行动项整理",
        "访谈解读、职场沟通、项目管理",
    ),
    (
        "知识检索",
        r"\brag\b|knowledge.base|knowledge.management|知识库|知识检索",
        "知识库检索与资料问答",
        "选题资料检索、出处核对与文献问答",
        "研究解读、百科知识、学习笔记",
    ),
    (
        "办公自动化",
        r"office.automat|workflow.automat|办公自动化|工作流自动化",
        "办公工作流自动化",
        "批量整理资料与重复办公任务",
        "效率工具、职场技能、自动化教程",
    ),
]
MEDIA_TAGS = {row[0] for row in CAPABILITIES[:10]}


class ProjectAnalysis(BaseModel):
    source: Literal["rules", "llm"] = "rules"
    version: str = "rules-v1"
    model: str | None = None
    domains: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    core_features: list[str] = Field(default_factory=list)
    use_cases: list[str] = Field(default_factory=list)
    knowledge_suggestions: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)


class ProjectAnalyzer(Protocol):
    def analyze(self, repo: dict, readme: str) -> ProjectAnalysis: ...


class RuleAnalyzer:
    def analyze(self, repo: dict, readme: str) -> ProjectAnalysis:
        text = f"{repo.get('full_name', '')}\n{repo.get('description') or ''}\n{' '.join(repo.get('topics', []))}\n{readme}"
        rows = [row for row in CAPABILITIES if re.search(row[1], text, re.I)]
        domains = []
        if any(row[0] in MEDIA_TAGS for row in rows):
            domains.append("AI短视频与影音制作")
        if any(row[0] not in MEDIA_TAGS for row in rows):
            domains.append("AI办公")
        return ProjectAnalysis(
            domains=domains,
            tags=[row[0] for row in rows],
            core_features=[row[2] for row in rows],
            use_cases=[row[3] for row in rows],
            knowledge_suggestions=list(dict.fromkeys(row[4] for row in rows)),
            evidence=[
                f"资料命中：{row[0]}（{re.search(row[1], text, re.I)[0][:100]}）" for row in rows
            ],
        )


def analyze_project(repo: dict, readme: str, analyzer: ProjectAnalyzer | None = None) -> dict:
    """注入模型适配器即可替换规则；结果独立保存于采集快照，不改写历史。"""
    result = (analyzer or RuleAnalyzer()).analyze(repo, readme)
    return ProjectAnalysis.model_validate(result).model_dump()
