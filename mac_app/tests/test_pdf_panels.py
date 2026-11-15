"""Run → Save lifecycle of the PDF tool panels, driven offscreen."""

import os
import threading
import time

import pytest
from PySide6.QtWidgets import QMessageBox

from gui.pdf_subpanels.flatten_panel import FlattenPanel
from gui.pdf_subpanels.resizer_panel import ResizerPanel
from gui.pdf_subpanels.splitter_panel import SplitterPanel


def _wait_until(qapp, condition, timeout=10.0):
    end = time.monotonic() + timeout
    while not condition():
        assert time.monotonic() < end, "timed out"
        qapp.processEvents()
        time.sleep(0.01)


def _run(qapp, panel, job):
    panel.run_job = job
    panel.run_btn.click()
    _wait_until(qapp, panel.run_btn.isEnabled)


def _writes(*names):
    """A run job that writes `names` into its temp folder."""

    def job(temp_dir, params, on_progress):
        paths = []
        for name in names:
            path = os.path.join(temp_dir, name)
            with open(path, "w") as f:
                f.write(name)
            paths.append(path)
        return paths

    return job


@pytest.fixture(autouse=True)
def _widgets(qwidgets):
    pass


@pytest.fixture
def answer(monkeypatch):
    """Returns a setter that stubs the overwrite question's reply and returns the list of questions asked."""
    asked = []

    def set_answer(reply):
        monkeypatch.setattr(QMessageBox, "question", lambda *args: asked.append(args) or reply)
        return asked

    return set_answer


def test_run_output_is_kept_when_the_input_is_unchanged(qapp, make_pdf):
    panel = FlattenPanel()
    panel.set_input(make_pdf("a", [200]))
    _run(qapp, panel, _writes("a-flattened.pdf"))
    assert panel.save_btn.isEnabled()


def test_run_output_is_dropped_when_the_input_changes_during_the_run(qapp, make_pdf):
    panel = FlattenPanel()
    panel.set_input(make_pdf("a", [200]))
    started, release = threading.Event(), threading.Event()
    write = _writes("a-flattened.pdf")

    def blocking_job(temp_dir, params, on_progress):
        started.set()
        release.wait(10)
        return write(temp_dir, params, on_progress)

    panel.run_job = blocking_job
    panel.run_btn.click()
    assert started.wait(10)
    panel.set_input(make_pdf("b", [200]))
    release.set()
    _wait_until(qapp, panel.run_btn.isEnabled)

    assert not panel.save_btn.isEnabled()
    assert "input changed" in panel.status_label.text()


def test_run_picks_up_an_input_typed_without_return(qapp, make_pdf):
    panel = FlattenPanel()
    panel.set_input(make_pdf("a", [200]))
    typed = make_pdf("b", [200])
    panel.input_edit.setText(typed)
    _run(qapp, panel, _writes("b-flattened.pdf"))
    assert panel.save_btn.isEnabled()
    assert panel.output_edit.placeholderText() == typed.replace(".pdf", "-flattened.pdf")


def test_resize_reference_page_ranges_over_the_input_pages(qapp, make_pdf):
    panel = ResizerPanel()
    panel.set_input(make_pdf("doc", [200, 300, 400]))
    assert panel.ref_page_spin.maximum() == 2
    panel.ref_page_spin.setValue(2)
    assert panel.params()["ref"] == 2


def test_save_copies_every_part_into_the_folder(qapp, make_pdf, tmp_path):
    panel = SplitterPanel()
    panel.set_input(make_pdf("doc", [200]))
    _run(qapp, panel, _writes("doc_1.pdf", "doc_2.pdf"))
    folder = tmp_path / "parts"
    panel.output_edit.setText(str(folder))
    panel.save_btn.click()
    assert sorted(os.listdir(folder)) == ["doc_1.pdf", "doc_2.pdf"]


def test_save_into_a_folder_target_checks_the_file_written(qapp, make_pdf, tmp_path, answer):
    panel = FlattenPanel()
    panel.set_input(make_pdf("doc", [200]))
    _run(qapp, panel, _writes("doc-flattened.pdf"))
    folder = tmp_path / "out"
    folder.mkdir()
    existing = folder / "doc-flattened.pdf"
    existing.write_text("keep me")
    panel.output_edit.setText(str(folder))

    asked = answer(QMessageBox.No)
    panel.save_btn.click()
    assert len(asked) == 1 and str(existing) in asked[0][2]
    assert existing.read_text() == "keep me"

    answer(QMessageBox.Yes)
    panel.save_btn.click()
    assert existing.read_text() == "doc-flattened.pdf"


def test_declined_overwrite_writes_no_part(qapp, make_pdf, tmp_path, answer):
    panel = SplitterPanel()
    panel.set_input(make_pdf("doc", [200]))
    _run(qapp, panel, _writes("doc_1.pdf", "doc_2.pdf"))
    folder = tmp_path / "parts"
    folder.mkdir()
    (folder / "doc_2.pdf").write_text("keep me")
    panel.output_edit.setText(str(folder))

    asked = answer(QMessageBox.No)
    panel.save_btn.click()
    assert len(asked) == 1
    assert sorted(os.listdir(folder)) == ["doc_2.pdf"]
    assert (folder / "doc_2.pdf").read_text() == "keep me"
