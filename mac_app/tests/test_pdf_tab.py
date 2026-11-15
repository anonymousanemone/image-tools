import os

import pymupdf

from gui.pdf_subpanels.base_panel import PreviewDoc, PreviewRequest
from gui.pdf_tab import PdfToolsTab, _doc_key, _render_preview


class _Panel:
    def __init__(self, path=None, error=None):
        self.path = path
        self.error = error

    def preview_job(self, request):
        if self.error:
            raise self.error
        return PreviewDoc(self.path)


def _request():
    return PreviewRequest({}, "original", [])


def test_render_preview_renders_a_new_document(qapp, make_pdf):
    path = make_pdf("doc", [300, 600])
    outcome = _render_preview(_Panel(path), _request(), shown_key=None)
    assert outcome.error is None
    assert [image.width() for image in outcome.images] == [500, 1000]


def test_render_preview_skips_rendering_the_shown_document(qapp, make_pdf):
    path = make_pdf("doc", [300])
    outcome = _render_preview(_Panel(path), _request(), shown_key=_doc_key(path))
    assert outcome.images is None and outcome.doc.path == path


def test_render_preview_rerenders_a_rewritten_file(qapp, make_pdf):
    path = make_pdf("doc", [300])
    shown_key = _doc_key(path)
    doc = pymupdf.open()
    doc.new_page(width=300, height=300)
    doc.new_page(width=300, height=300)
    doc.save(path + ".new")
    doc.close()
    os.replace(path + ".new", path)

    outcome = _render_preview(_Panel(path), _request(), shown_key=shown_key)
    assert outcome.images is not None and len(outcome.images) == 2


def test_render_preview_reports_errors():
    outcome = _render_preview(_Panel(error=ValueError("page counts differ")), _request(), shown_key=None)
    assert outcome.error == "page counts differ" and outcome.images is None


def test_tab_shares_the_input_with_every_tool(qwidgets, make_pdf):
    tab = PdfToolsTab()
    path = make_pdf("doc", [300])
    tab.stack.currentWidget().set_input(path)
    tab._preview_pool.waitForDone()
    panels = [tab.stack.widget(i) for i in range(tab.stack.count())]
    assert [panel.input_edit.text() for panel in panels] == [path] * len(panels)
