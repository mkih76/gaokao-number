"""
薄弱点诊断模块 — 单元测试
"""
import sys
import os
import json
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.question_db import QuestionDB
from src.diagnose import run_diagnosis


@pytest.fixture
def mock_qdb():
    """创建模拟题库"""
    questions = [
        {
            "qid": "hecha-beibi_d01",
            "question_type": "hecha-beibi",
            "difficulty": 2,
            "source": "诊断题",
            "stem": "测试题1",
            "options": {"A": "1", "B": "2", "C": "3", "D": "4"},
            "answer": "A",
            "solution": "解析",
            "method": "代入法",
            "tags": ["测试"]
        },
        {
            "qid": "gongcheng_d01",
            "question_type": "gongcheng",
            "difficulty": 1,
            "source": "诊断题",
            "stem": "测试题2",
            "options": {"A": "1", "B": "2", "C": "3", "D": "4"},
            "answer": "B",
            "solution": "解析",
            "method": "方程法",
            "tags": ["测试"]
        },
        {
            "qid": "xingcheng_d01",
            "question_type": "xingcheng",
            "difficulty": 2,
            "source": "诊断题",
            "stem": "测试题3",
            "options": {"A": "1", "B": "2", "C": "3", "D": "4"},
            "answer": "C",
            "solution": "解析",
            "method": "比例法",
            "tags": ["测试"]
        },
        {
            "qid": "pailie-zuhe_d01",
            "question_type": "pailie-zuhe",
            "difficulty": 3,
            "source": "诊断题",
            "stem": "测试题4",
            "options": {"A": "1", "B": "2", "C": "3", "D": "4"},
            "answer": "D",
            "solution": "解析",
            "method": "排列法",
            "tags": ["测试"]
        },
        {
            "qid": "gailv_d01",
            "question_type": "gailv",
            "difficulty": 2,
            "source": "诊断题",
            "stem": "测试题5",
            "options": {"A": "1", "B": "2", "C": "3", "D": "4"},
            "answer": "A",
            "solution": "解析",
            "method": "古典概型",
            "tags": ["测试"]
        },
    ]

    # 写入临时文件
    tmp_path = "/tmp/test_questions.json"
    with open(tmp_path, "w") as f:
        json.dump({"questions": questions}, f, ensure_ascii=False)

    qdb = QuestionDB(tmp_path)
    return qdb


class TestDiagnose:
    """诊断引擎测试"""

    def test_all_correct(self, mock_qdb):
        """全对（5题全对，score=5，默认推荐60天）"""
        answers = {
            "hecha-beibi_d01": "A",
            "gongcheng_d01": "B",
            "xingcheng_d01": "C",
            "pailie-zuhe_d01": "D",
            "gailv_d01": "A",
        }
        result = run_diagnosis(answers, mock_qdb)

        assert result["score"] == 5
        assert result["total"] == 5

        # 5/5得分=score<=5，按诊断逻辑推荐60天
        # 实际15题全对时会推荐14天

        # 检查题型统计
        for qtype, wp in result["weak_points"].items():
            assert wp["correct"] == wp["total"], f"{qtype} 应全对"
            assert wp["rate"] == 1.0

    def test_all_wrong(self, mock_qdb):
        """全错的情况，应推荐60天"""
        answers = {
            "hecha-beibi_d01": "B",
            "gongcheng_d01": "C",
            "xingcheng_d01": "D",
            "pailie-zuhe_d01": "A",
            "gailv_d01": "B",
        }
        result = run_diagnosis(answers, mock_qdb)

        assert result["score"] == 0
        assert result["recommended_plan"] == "60days"

        # 所有题型应为 weak
        for qtype, wp in result["weak_points"].items():
            assert wp["level"] == "weak"

    def test_partial_mix(self, mock_qdb):
        """部分正确"""
        answers = {
            "hecha-beibi_d01": "A",  # 正确
            "gongcheng_d01": "C",    # 错误 (应为B)
            "xingcheng_d01": "C",    # 正确
            "pailie-zuhe_d01": "A",  # 错误 (应为D)
            "gailv_d01": "A",        # 正确
        }
        result = run_diagnosis(answers, mock_qdb)
        assert result["score"] == 3

    def test_output_structure(self, mock_qdb):
        """验证输出结构完整性"""
        answers = {
            "hecha-beibi_d01": "A",
            "gongcheng_d01": "B",
            "xingcheng_d01": "C",
            "pailie-zuhe_d01": "D",
            "gailv_d01": "A",
        }
        result = run_diagnosis(answers, mock_qdb)

        # 必须包含的字段
        required_fields = ["score", "total", "detail", "weak_points", "summary", "priority", "recommended_plan"]
        for field in required_fields:
            assert field in result, f"缺少字段: {field}"

        # weak_points 的子结构
        for qtype, wp in result["weak_points"].items():
            for sub in ["correct", "total", "rate", "level", "name"]:
                assert sub in wp, f"弱項点缺少字段: {qtype}.{sub}"

        # priority 的子结构
        for p in result["priority"]:
            for sub in ["type", "name", "rate", "urgency", "reason"]:
                assert sub in p, f"优先级缺少字段: {sub}"
