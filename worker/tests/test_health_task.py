from common.tasks import health_check


def test_health_check_task_runs_synchronously_without_broker():
    # `.run()` executes the task body directly, without requiring a live
    # broker connection, so this test stays fast and hermetic.
    result = health_check.run()
    assert result == {"status": "ok"}
