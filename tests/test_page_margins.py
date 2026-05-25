import os
import sys
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "chemcanvas")))

from PyQt5.QtWidgets import QApplication

from document import Page
from paper import Paper


app = QApplication.instance() or QApplication(sys.argv)


class DummyObject:
    def __init__(self, bbox):
        self._bbox = bbox

    def bounding_box(self):
        return self._bbox


class PageMarginTest(unittest.TestCase):
    def setUp(self):
        self.paper = Paper()

    def test_printable_rect_uses_independent_page_margins(self):
        self.paper.pages = [Page(page_w=200, page_h=100, margins=(10, 20, 30, 40), objects=[])]
        self.paper._rebuild_page_layout()

        self.assertEqual(self.paper.page_printable_rect(0), (60, 30, 200, 90))
        self.assertEqual(self.paper.page_printable_rect_local(0), (40, 10, 180, 70))

    def test_margin_guides_are_created_as_non_printing_items(self):
        self.paper.pages = [Page(page_w=200, page_h=100, margins=(10, 20, 30, 40), objects=[])]
        self.paper._rebuild_page_layout()

        self.assertEqual(len(self.paper._margin_guides), 1)
        self.assertIn(self.paper._margin_guides[0], self.paper.nonPrintingItems())

    def test_automatic_placement_stays_inside_printable_area(self):
        self.paper.pages = [Page(page_w=200, page_h=100, margins=(10, 20, 30, 40), objects=[])]
        self.paper._rebuild_page_layout()

        x, y = self.paper.find_place_for_obj_size(20, 10, page_index=0)
        left, top, right, bottom = self.paper.page_printable_rect_local(0)

        self.assertGreaterEqual(x, left)
        self.assertGreaterEqual(y, top)
        self.assertLessEqual(x + 20, right)
        self.assertLessEqual(y + 10, bottom)

    def test_detects_objects_outside_printable_margins(self):
        inside = DummyObject((70, 40, 100, 60))
        outside = DummyObject((55, 40, 80, 60))
        self.paper.pages = [Page(page_w=200, page_h=100, margins=(10, 20, 30, 40),
                                 objects=[inside, outside])]
        self.paper._rebuild_page_layout()

        self.assertEqual(self.paper.objects_outside_margins(), [outside])


if __name__ == "__main__":
    unittest.main()
