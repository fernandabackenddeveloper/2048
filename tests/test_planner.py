from orchestrator.planning import generate_plan


def test_generate_plan_has_milestones_and_tasks() -> None:
    plan = generate_plan("Build something web", project="x", stack="web_fullstack")
    assert plan["project"] == "x"
    assert plan["stack"] == "web_fullstack"
    assert len(plan["milestones"]) >= 3

    task_count = 0
    for ms in plan["milestones"]:
        for feat in ms["features"]:
            task_count += len(feat["tasks"])
    assert task_count >= 4
