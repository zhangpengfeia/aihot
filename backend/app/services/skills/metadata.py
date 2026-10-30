"""Skills 用途分类和安装信息摘录；所有命令只作为资料保存，绝不执行。"""

import re

SKILL_CATEGORIES = ["脚本写作", "配音", "字幕", "动画", "剪辑", "其他"]
RULES = {
    "脚本写作": r"scriptwriting|screenplay|copywriting|storytelling|脚本写作|文案|剧本",
    "配音": r"text.to.speech|\btts\b|voiceover|voice.clon|配音|语音合成",
    "字幕": r"subtitle|caption|transcri|\bsrt\b|\basr\b|字幕|转录",
    "动画": r"animation|motion.graphics|remotion|manim|动画|动效",
    "剪辑": r"video.edit|video.process|ffmpeg|剪辑|视频处理",
}


def extract_metadata(name: str, description: str, readme: str) -> tuple[list[str], str]:
    """多标签规则匹配会产生误判，前端明确标注，分类不等于功能实测。"""
    text = f"{name}\n{description}\n{readme}"
    categories = [label for label, rule in RULES.items() if re.search(rule, text, re.I)]
    # 优先保留安装章节，遇到同级或上级标题结束，避免把后续所有内容误作安装说明。
    lines = readme.splitlines()
    instructions = []
    for index, line in enumerate(lines):
        heading = re.match(r"^(#{1,6})\s+(.+)", line)
        if not heading or not re.search(
            r"install|setup|getting.started|quick.start|安装|快速开始", heading[2], re.I
        ):
            continue
        instructions = [line]
        level = len(heading[1])
        for next_line in lines[index + 1 :]:
            if re.match(rf"^#{{1,{level}}}\s", next_line):
                break
            instructions.append(next_line)
        break
    return categories or ["其他"], "\n".join(instructions)[
        :6000
    ] or "README 中未定位到安装章节，请查看原始仓库文档。"
