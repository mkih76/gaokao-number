"""
题库引擎模块
从 questions.json 加载完整题库，提供多维度查询
"""
import json
import random
from typing import Optional


class QuestionNotFoundError(Exception):
    """题目不存在"""
    pass


class QuestionDB:
    """题库引擎"""

    TYPE_NAMES = {
        "hecha-beibi": "和差倍比",
        "gongcheng": "工程问题",
        "xingcheng": "行程问题",
        "pailie-zuhe": "排列组合",
        "gailv": "概率问题",
        "jihe": "几何问题",
        "jingji-lirun": "经济利润",
        "rongye": "溶液问题",
        "rongchi": "容斥原理",
        "riqi-nianling": "日期年龄",
        "chouti": "抽屉原理",
        "jitu-tonglong": "鸡兔同笼",
        "heding-jizhi": "和定极值",
    }

    PRIORITY = {
        "hecha-beibi": "P0", "gongcheng": "P0", "xingcheng": "P0",
        "pailie-zuhe": "P1", "gailv": "P1", "jihe": "P1", "jingji-lirun": "P1",
        "rongye": "P2", "rongchi": "P2", "riqi-nianling": "P2",
        "chouti": "P3", "jitu-tonglong": "P3", "heding-jizhi": "P3",
    }

    def __init__(self, data_path: str = "data/questions.json"):
        with open(data_path, "r") as f:
            raw = json.load(f)
        self.questions: list[dict] = raw if isinstance(raw, list) else raw.get("questions", [])
        self._by_id = {q["qid"]: q for q in self.questions}

    def get_by_id(self, qid: str) -> Optional[dict]:
        q = self._by_id.get(qid)
        if not q:
            raise QuestionNotFoundError(f"题目 {qid} 不存在")
        return q

    def get_by_ids(self, qids: list[str]) -> list[dict]:
        return [self.get_by_id(qid) for qid in qids if qid in self._by_id]

    def get_by_type(self, qtype: str) -> list[dict]:
        return [q for q in self.questions if q["question_type"] == qtype]

    def get_by_difficulty(self, level: int) -> list[dict]:
        return [q for q in self.questions if q["difficulty"] == level]

    def get_by_tags(self, tags: list[str]) -> list[dict]:
        return [q for q in self.questions if any(t in (q.get("tags") or []) for t in tags)]

    def get_diagnosis_questions(self) -> list[dict]:
        """选取15道诊断题，覆盖13种题型，按优先级分配"""
        picks = []
        # P0题型各2道，P1各1道，P2/P3各1道
        strategy = {
            "hecha-beibi": 2, "gongcheng": 2, "xingcheng": 2,
            "pailie-zuhe": 1, "gailv": 1, "jihe": 1, "jingji-lirun": 1,
            "rongye": 1, "rongchi": 1, "riqi-nianling": 1,
            "chouti": 1, "heding-jizhi": 1,
        }
        for qtype, count in strategy.items():
            pool = self.get_by_type(qtype)
            random.shuffle(pool)
            picks.extend(pool[:count])
        random.shuffle(picks)
        return picks[:15]

    def random_pick(self, n: int, exclude: Optional[list[str]] = None) -> list[dict]:
        pool = [q for q in self.questions if q["qid"] not in (exclude or [])]
        random.shuffle(pool)
        return pool[:n]

    def get_statistics(self) -> dict:
        """题库统计"""
        type_counts = {}
        difficulty_counts = {}
        for q in self.questions:
            t = q["question_type"]
            type_counts[t] = type_counts.get(t, 0) + 1
            d = q["difficulty"]
            difficulty_counts[d] = difficulty_counts.get(d, 0) + 1
        return {
            "total": len(self.questions),
            "by_type": type_counts,
            "by_difficulty": difficulty_counts,
        }

    def get_priority_order(self) -> list[str]:
        """按优先级返回题型列表"""
        return sorted(self.PRIORITY.keys(), key=lambda t: self.PRIORITY[t])
