from gui.workers import Worker


def _run(fn):
    results, errors = [], []
    worker = Worker(fn)
    worker.signals.result.connect(results.append)
    worker.signals.error.connect(errors.append)
    worker.run()
    return results, errors


def test_worker_emits_result_on_success():
    assert _run(lambda on_progress: ["out.pdf"]) == ([["out.pdf"]], [])


def test_worker_emits_only_error_on_failure():
    def fail(on_progress):
        raise ValueError("bad page")

    assert _run(fail) == ([], ["bad page"])
