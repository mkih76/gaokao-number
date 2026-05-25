"""
学习路径生成 — 单元测试
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.path_planner import generate_path, get_day_tasks


class TestPathPlanner:
    """学习路径生成测试"""

    def test_21days_path_length(self):
        """21天路径应为21天"""
        mock_diagnosis = {
            "score": 8,
            "total": 15,
            "priority": [],
        }
        path = generate_path(mock_diagnosis, "21days")
        assert len(path) == 21, f"21天路径长度应为21，实际{len(path)}"

    def test_14days_path_length(self):
        """14天路径应为14天"""
        mock_diagnosis = {
            "score": 12,
            "total": 15,
            "priority": [],
        }
        path = generate_path(mock_diagnosis, "14days")
        assert len(path) == 14, f"14天路径长度应为14，实际{len(path)}"

    def test_path_structure(self):
        """验证路径条目结构"""
        mock_diagnosis = {"score": 8, "total": 15, "priority": []}
        path = generate_path(mock_diagnosis, "21days")

        for entry in path:
            assert "day" in entry, "缺少 day 字段"
            assert "topics" in entry, "缺少 topics 字段"
            assert "difficulty" in entry, "缺少 difficulty 字段"
            assert "status" in entry, "缺少 status 字段"
            assert 1 <= entry["difficulty"] <= 5, f"难度超出范围: {entry['difficulty']}"

            # topics 不能为空
            assert len(entry["topics"]) > 0, f"第{entry['day']}天内容为空"

    def test_path_increasing_difficulty(self):
        """难度应随天数递增（总体趋势）"""
        mock_diagnosis = {"score": 8, "total": 15, "priority": []}
        path = generate_path(mock_diagnosis, "21days")

        first_week_avg = sum(e["difficulty"] for e in path[:7]) / 7
        last_week_avg = sum(e["difficulty"] for e in path[-7:]) / 7

        assert last_week_avg >= first_week_avg, \
            f"最后一周难度平均值({last_week_avg:.1f})应不低于第一周({first_week_avg:.1f})"

    def test_weak_type_adjustment(self):
        """薄弱题型应被加入到复习日中"""
        mock_diagnosis = {
            "score": 3,
            "total": 15,
            "priority": [
                {"type": "xingcheng", "name": "行程问题", "rate": 0.0, "urgency": "high", "reason": "0/2"},
                {"type": "pailie-zuhe", "name": "排列组合", "rate": 0.0, "urgency": "high", "reason": "0/1"},
            ],
        }
        path = generate_path(mock_diagnosis, "21days")

        # 检查是否有包含"薄弱"或"专攻"字样的条目
        review_entries = [e for e in path if e.get("is_review") or any("薄弱" in t for t in e["topics"])]
        assert len(review_entries) > 0, "薄弱题型应有专项复习日"

    def test_60days_path_length(self):
        """60天路径长度应≥60"""
        mock_diagnosis = {"score": 3, "total": 15, "priority": []}
        path = generate_path(mock_diagnosis, "60days")
        assert len(path) >= 60, f"60天路径长度应≥60，实际{len(path)}"

    def test_get_day_tasks(self):
        """应能正确获取某天的任务"""
        mock_diagnosis = {"score": 8, "total": 15, "priority": []}
        path = generate_path(mock_diagnosis, "21days")

        day3 = get_day_tasks(path, 3)
        assert day3 is not None
        assert day3["day"] == 3

        # 不存在的天
        day99 = get_day_tasks(path, 99)
        assert day99 is None

    def test_priority_order(self):
        """P0题型应出现在P1题型之前"""
        mock_diagnosis = {"score": 8, "total": 15, "priority": []}
        path = generate_path(mock_diagnosis, "21days")

        # 找到第一个出现 P0 和 P1 的题型
        p0_days = []
        p1_days = []
        from src.question_db import QuestionDB
        priority_map = QuestionDB.PRIORITY

        for entry in path:
            types = entry.get("types", [])
            for t in types:
                pri = priority_map.get(t, "P9")
                if pri == "P0":
                    p0_days.append(entry["day"])
                elif pri == "P1":
                    p1_days.append(entry["day"])

        if p0_days and p1_days:
            assert max(p0_days) < min(p1_days), \
                f"P0题型最后出现天数({max(p0_days)})应早于P1题型首次出现天数({min(p1_days)})"
