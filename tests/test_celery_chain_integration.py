import sys
import types
from unittest.mock import patch

from project.apps.core.tasks import build_daily_ml_chain


def test_celery_chain_order():
    fake_ingestion = types.ModuleType("project.apps.ingestion.tasks")

    class FakeDownload:
        task = "project.apps.ingestion.tasks.download_bhavcopy"

        @staticmethod
        def s(run_date):
            from celery import Signature

            return Signature(FakeDownload.task, (run_date,), {})

    fake_ingestion.download_bhavcopy = FakeDownload()
    sys.modules["project.apps.ingestion.tasks"] = fake_ingestion

    with patch("project.apps.core.tasks.chain") as mock_chain:
        build_daily_ml_chain("12052026")

    signatures = mock_chain.call_args.args
    task_names = [sig.task for sig in signatures]
    assert task_names == [
        "project.apps.ingestion.tasks.download_bhavcopy",
        "project.apps.core.tasks.compute_features",
        "project.apps.core.tasks.generate_labels",
        "project.apps.core.tasks.train_models",
        "project.apps.core.tasks.generate_rankings",
        "project.apps.core.tasks.run_backtests",
        "project.apps.core.tasks.monitor_drift",
    ]
