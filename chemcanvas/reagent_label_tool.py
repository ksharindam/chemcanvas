# -*- coding: utf-8 -*-
# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2026 Arindam Chaudhuri <arindamsoft94@gmail.com>
import os, re
from functools import reduce
import operator

from PyQt5.QtCore import QRectF, Qt, QPointF, QMarginsF, pyqtSignal, QSize
from PyQt5.QtGui import (QPainter, QColor, QPen, QBrush, QPixmap, QIcon,
    QTextDocument, QTextOption, QPdfWriter, QFont, QPainterPath, QTransform)
from PyQt5.QtWidgets import (QDialog, QToolBar, QVBoxLayout, QAction, QWidget,
    QGridLayout, QDialogButtonBox, QLabel, QLineEdit, QCheckBox, QPushButton,
    QGraphicsView, QGraphicsScene, QGraphicsTextItem, QGraphicsRectItem,
    QStyleOptionGraphicsItem, QGraphicsItemGroup, QFileDialog, QStatusBar,
    QDoubleSpinBox, QHBoxLayout, QSpacerItem, QToolButton, QComboBox, QFontComboBox,
    QGraphicsPathItem, QGraphicsPixmapItem)
from PyQt5.QtPrintSupport import QPrinter, QPrintDialog


class LabelPrintDialog(QDialog):
    def __init__(self):
        QDialog.__init__(self)
        self.setWindowTitle("Print Chemical Label")
        self.setWindowIcon(QIcon(":/icons/print.png"))
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6,0,0,0)
        toolbar = QToolBar()
        toolbar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        #toolbar.setIconSize(QSize(24,24))
        layout.setMenuBar(toolbar)
        self.savePdfAction = QAction(QIcon(":/icons/pdf.png"), "Save PDF", self)
        toolbar.addAction(self.savePdfAction)
        self.printAction = QAction(QIcon(":/icons/print.png"), "Print", self)
        toolbar.addAction(self.printAction)
        toolbar.addSeparator()
        self.newLabelAction = QAction(QIcon(":/icons/new-file.png"), "New", self)
        toolbar.addAction(self.newLabelAction)
        self.duplicateLabelAction = QAction(QIcon(":/icons/copy.png"), "Duplicate", self)
        toolbar.addAction(self.duplicateLabelAction)
        self.editLabelAction = QAction(QIcon(":/icons/edit.png"), "Edit", self)
        toolbar.addAction(self.editLabelAction)
        self.deleteLabelAction = QAction(QIcon(":/icons/delete.png"), "Delete", self)
        toolbar.addAction(self.deleteLabelAction)
        self.settingsAction = QAction(QIcon(":/icons/settings.png"), "Settings", self)
        toolbar.addAction(self.settingsAction)
        toolbar.addSeparator()
        self.quitAction = QAction(QIcon(":/icons/quit.png"), "Quit", self)
        toolbar.addAction(self.quitAction)
        spacer = QWidget(toolbar)
        spacer.setSizePolicy(1|2|4,1|4)
        toolbar.addWidget(spacer)
        self.statusWidget = QLabel(toolbar)
        toolbar.addWidget(self.statusWidget)
        # setup graphics view
        self.graphicsView = QGraphicsView(self)
        self.graphicsView.setMouseTracking(True)
        self.graphicsView.setBackgroundBrush(Qt.gray)
        self.graphicsView.setAlignment(Qt.AlignHCenter)
        # this improves drawing speed
        self.graphicsView.setViewportUpdateMode(QGraphicsView.BoundingRectViewportUpdate)
        # makes small circles and objects smoother
        self.graphicsView.setRenderHint(QPainter.Antialiasing, True)
        self.paper = LabelPaper(self.graphicsView)
        # layout widgets
        layout.addWidget(self.graphicsView)
        # connect signals
        self.paper.statusMessageChanged.connect(self.showMessage)
        self.savePdfAction.triggered.connect(self.savePdf)
        self.printAction.triggered.connect(self.printLabel)
        self.newLabelAction.triggered.connect(self.newLabel)
        self.duplicateLabelAction.triggered.connect(self.duplicateLabel)
        self.settingsAction.triggered.connect(self.openSettings)
        self.quitAction.triggered.connect(self.accept)
        # init values
        self.label_size = (5.0,2.5)
        self.border_w = 0.3
        self.border_rounded = False
        self.heading_font = QFont("DejaVu Serif")
        self.body_font = self.heading_font
        self.resize(900, 480)
        self.paper.updateStatus()

    def newLabel(self):
        dlg = NewLabelDialog(self)
        dlg.setValues(self.label_size, self.border_w, self.border_rounded,
                    (self.heading_font,self.body_font))
        if dlg.exec()==dlg.Accepted:
            self.paper.addLabel(dlg.getLabel())
            self.label_size, self.border_w, self.border_rounded, fonts = dlg.getValues()
            self.heading_font, self.body_font = fonts

    def duplicateLabel(self):
        print("duplicate")

    def openSettings(self):
        dlg = SettingsDialog(self)
        dlg.setValues(self.paper.page_size_name, self.paper.custom_size,
                    self.paper.margin, self.paper.spacing)
        if dlg.exec()==QDialog.Accepted:
            page_size, custom_size, margin, spacing = dlg.getValues()
            self.paper.page_size_name = page_size
            self.paper.custom_size = custom_size
            self.paper.margin = margin
            self.paper.spacing = spacing
            self.paper.updatePageSize()

    def savePdf(self):
        path = self.get_new_filename("label.pdf")
        filename, filtr = QFileDialog.getSaveFileName(self, "Save File",
                        path, "Portable Document Format (*.pdf)")
        if not filename:
            return
        writer = QPdfWriter(filename)
        #writer.setPageSize(QPageSize(QSize(int(page_w), int(page_h))))
        writer.setPageSize(QPdfWriter.A4)
        writer.setCreator("ChemCanvas")
        writer.setTitle("ChemCanvas Chemical Label")
        layout = writer.pageLayout()
        layout.setMargins(QMarginsF(1, 1, 1, 1))
        writer.setPageLayout(layout)

        painter = QPainter(writer)
        self.paper.render(painter)
        painter.end()


    def printLabel(self):
        printer = QPrinter(QPrinter.HighResolution)
        dlg = QPrintDialog(printer, self)
        # disable some options (PrintSelection, PrintCurrentPage are disabled by default)
        dlg.setOption(QPrintDialog.PrintPageRange, False)
        dlg.setOption(QPrintDialog.PrintCollateCopies, False)
        if dlg.exec() == QDialog.Accepted:
            painter = QPainter(printer)
            rect = painter.viewport()# area inside margin
            # input page size @ printer dpi
            page_w_px = int(printer.physicalDpiX()*self.paper.page_size[0]/72)
            page_h_px = int(printer.physicalDpiY()*self.paper.page_size[1]/72)
            scale = rect.height()/page_h_px
            transform = QTransform.fromScale(scale, scale)
            #transform.translate(rect.x(), rect.y())
            painter.setTransform(transform)
            self.paper.render(painter)
            painter.end()


    def get_new_filename(self, filename):
        """ get a new filename with number suffix if filename already exists """
        basename, ext = os.path.splitext(filename)# ext includes dot
        path = filename
        i = 1
        while os.path.exists(path):
            path = "%s-%i%s" % (basename, i, ext)
            i += 1
        return path

    def showMessage(self, msg):
        self.statusWidget.setText(msg)


class LabelPaper(QGraphicsScene):
    """ The canvas on which all items are drawn """
    statusMessageChanged = pyqtSignal(str)
    def __init__(self, view):
        QGraphicsScene.__init__(self, view)
        self.view = view
        view.setScene(self)
        self.page_size_name = "A4"
        self.custom_size = (21.0,29.7)# cm
        self.page_size = (595,842)# points
        self.page_w, self.page_h = 826, 1169 # px @100dpi
        self.margin = 3.0 # mm
        self.spacing = 1.2 # mm
        self.labels = []
        self.mouse_press_pos = None
        self.selected = None
        self.mode = None
        self.paper = None
        self.updatePageSize()

    def updatePageSize(self):
        custom_w = int(round(self.custom_size[0]/2.54*72))
        custom_h = int(round(self.custom_size[1]/2.54*72))
        page_sizes = {"A4": (595,842), "A5": (420,595), "A6": (298,420),
                        "A7": (210,298), "4R": (288,432), "L": (252,360),
                        "Letter":(612,792), "Custom": (custom_w, custom_h)}
        page_size = page_sizes[self.page_size_name]
        if self.paper and page_size == self.page_size:
            return
        self.page_size = page_size
        self.page_w = self.page_size[0]/72*100
        self.page_h = self.page_size[1]/72*100
        self.setSceneRect(0,0, self.page_w, self.page_h)
        if not self.paper:
            self.paper = self.addRect(self.sceneRect(), Qt.white, Qt.white)
        else:
            self.paper.setRect(self.sceneRect())
        self.updateStatus()


    def addLabel(self, label):
        group = QGraphicsItemGroup()
        for item in label.items:
            group.addToGroup(item)
        self.addItem(group)
        label.item_group = group
        group.object = label
        # place label in empty position
        w, h = label.size
        x,y = self.find_position(w,h)
        label.moveBy(x,y)
        self.labels.append(label)

    def selectLabel(self, label):
        if label==self.selected:
            return
        if self.selected:
            self.selected.setSelected(False)
            self.selected = None
        if label:
            self.selected = label
            self.selected.setSelected(True)
        self.updateStatus()


    def mousePressEvent(self, ev):
        if ev.button() != Qt.LeftButton:
            return QGraphicsScene.mousePressEvent(self, ev)
        pos = ev.scenePos()
        self.mouse_press_pos = pos
        self.prev_pos = pos.x(), pos.y()
        objs = [item.object for item in self.items(pos) if hasattr(item,"object")]
        obj = objs[0] if objs else None
        if obj:
            self.selectLabel(obj)
            if obj.draggingCorner(pos):
                self.mode = "resize"
                self.obj_rect = obj.boundingBox()
            else:
                self.mode = "move"
        else:
            self.selectLabel(None)
        QGraphicsScene.mousePressEvent(self, ev)


    def mouseMoveEvent(self, ev):
        pos = ev.scenePos()
        x, y = pos.x(), pos.y()
        if self.mode=="move":
            self.selected.moveBy(x-self.prev_pos[0], y-self.prev_pos[1])
            self.prev_pos = x, y
        elif self.mode=="resize":
            diff = pos - self.mouse_press_pos
            rect = self.obj_rect.adjusted(0,0,diff.x(),diff.y())
            self.selected.scaleToFit(rect.width(), rect.height())
            self.updateStatus()
        QGraphicsScene.mouseMoveEvent(self, ev)


    def mouseReleaseEvent(self, ev):
        self.mouse_press_pos = None
        #self.selected = None
        self.mode = None
        QGraphicsScene.mouseReleaseEvent(self, ev)


    def updateStatus(self):
        msg = ""
        if self.selected:
            rect = self.selected.boundingBox()
            w = round(rect.width()*0.0254, 1)
            h = round(rect.height()*0.0254, 1)
            msg = "Label Size : %.1fx%.1f ;  "%(w,h)
        page_size = self.page_size_name
        if page_size == "Custom":
            page_size = "%gx%gcm" % self.custom_size
        msg += "Page Size : %s" % page_size
        self.statusMessageChanged.emit(msg)

    def find_position(self, w, h):
        spacing, margin = self.spacing/25.4*100, self.margin/25.4*100
        if not self.labels:
            return margin, margin
        # get lowest label
        rects = [label.boundingBox() for label in self.labels]
        rects.sort(key=lambda r:r.bottom())
        # get last row by getting labels along the center of the lowest label
        cy = rects[-1].center().y()
        lowest_rects = [rect for rect in rects if rect.top()<cy and rect.bottom()>cy]
        lowest_rects.sort(key=lambda l:l.right())# rightmost in last row
        # if does not fit in same line, place in next row
        if self.page_w - lowest_rects[-1].right() < w+spacing+margin:
            lowest_rects.sort(key=lambda l:l.bottom())
            y = lowest_rects[-1].bottom() + spacing
            x = margin
            if y>self.page_h-h:
                y = self.page_h-h-margin
            return x,y
        # place in same line
        pos = lowest_rects[-1].topRight() + QPointF(spacing,0)
        return pos.x(), pos.y()



class Label:
    def __init__(self, size):
        self.size = size
        self.items = []
        self.item_group = None

    def boundingBox(self):
        return self.item_group.sceneBoundingRect()

    def moveBy(self, dx,dy):
        self.item_group.moveBy(dx,dy)

    def draggingCorner(self, pos):
        p2 = self.boundingBox().bottomRight()
        p1 = p2 - QPointF(20,20)# top left
        return QRectF(p1, p2).contains(pos)


    def scaleToFit(self, w, h):
        scale_x = w/self.size[0]
        scale_y = h/self.size[1]
        scale = min(scale_x, scale_y)
        self.item_group.resetTransform()
        self.item_group.setScale(scale)

    def setSelected(self, select):
        brush = QBrush(QColor(255,255,150)) if select else Qt.white
        self.items[0].setBrush(brush)


class SettingsDialog(QDialog):
    def __init__(self, parent):
        QDialog.__init__(self, parent)
        self.setWindowTitle("Settings")
        self.setWindowIcon(QIcon(":/icons/settings.png"))
        self.pageSizeLabel = QLabel("Page Size :", self)
        self.pageSizeCombo = QComboBox(self)
        self.pageSizeCombo.addItems(["A4", "A5", "A6", "A7", "L", "4R", "Letter", "Custom"])
        self.customWidthSpin = QDoubleSpinBox(self)
        self.customWidthSpin.setDecimals(1)
        self.customWidthSpin.setSingleStep(0.5)
        self.customWidthSpin.setSuffix(" cm")
        self.customWidthSpin.setRange(2, 50)
        self.customHeightSpin = QDoubleSpinBox(self)
        self.customHeightSpin.setDecimals(1)
        self.customHeightSpin.setSingleStep(0.5)
        self.customHeightSpin.setSuffix(" cm")
        self.customHeightSpin.setRange(2, 50)
        self.marginLabel = QLabel("Margin :", self)
        self.marginSpin = QDoubleSpinBox(self)
        self.marginSpin.setDecimals(1)
        self.marginSpin.setSingleStep(0.5)
        self.marginSpin.setSuffix(" mm")
        self.marginSpin.setRange(0, 30)
        self.spacingLabel = QLabel("Spacing :", self)
        self.spacingSpin = QDoubleSpinBox(self)
        self.spacingSpin.setDecimals(1)
        self.spacingSpin.setSingleStep(0.5)
        self.spacingSpin.setSuffix(" mm")
        self.spacingSpin.setRange(1, 30)
        self.btnBox = QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel, parent=self)
        layout = QGridLayout(self)
        layout.addWidget(self.pageSizeLabel, 0,0)
        layout.addWidget(self.pageSizeCombo, 0,1)
        layout.addWidget(self.customWidthSpin, 1,0)
        layout.addWidget(self.customHeightSpin, 1,1)
        layout.addWidget(self.marginLabel, 2,0)
        layout.addWidget(self.marginSpin, 2,1)
        layout.addWidget(self.spacingLabel, 3,0)
        layout.addWidget(self.spacingSpin, 3,1)
        layout.addWidget(self.btnBox, 4,0,1,2)
        # connect signals
        self.pageSizeCombo.currentIndexChanged[str].connect(self.onPageSizeChange)
        self.btnBox.accepted.connect(self.accept)
        self.btnBox.rejected.connect(self.reject)
        # init values
        self.customWidthSpin.setVisible(False)
        self.customHeightSpin.setVisible(False)

    def onPageSizeChange(self, val):
        self.customWidthSpin.setVisible(val=="Custom")
        self.customHeightSpin.setVisible(val=="Custom")

    def getValues(self):
        page_size = self.pageSizeCombo.currentText()
        custom_w = self.customWidthSpin.value()
        custom_h = self.customHeightSpin.value()
        margin = self.marginSpin.value()
        spacing = self.spacingSpin.value()
        return page_size, (custom_w, custom_h), margin, spacing

    def setValues(self, page_size, custom_size, margin, spacing):
        self.pageSizeCombo.setCurrentIndex(self.pageSizeCombo.findText(page_size))
        self.customWidthSpin.setValue(custom_size[0])
        self.customHeightSpin.setValue(custom_size[1])
        self.marginSpin.setValue(margin)
        self.spacingSpin.setValue(spacing)



class NewLabelDialog(QDialog):
    def __init__(self, parent):
        QDialog.__init__(self, parent)
        self.setWindowTitle("New Label")
        self.setWindowIcon(QIcon(":/icons/new-file.png"))
        self.resize(500,150)
        layout = QGridLayout(self)
        # size properties
        self.propertiesWidget = QWidget(self)
        self.widthLabel = QLabel("Size (cm) :", self.propertiesWidget)
        self.widthSpin = QDoubleSpinBox(self.propertiesWidget)
        self.widthSpin.setRange(1.0,15.0)
        self.widthSpin.setDecimals(1)
        self.widthSpin.setSingleStep(0.5)
        self.heightLabel = QLabel("x", self.propertiesWidget)
        self.heightSpin = QDoubleSpinBox(self.propertiesWidget)
        self.heightSpin.setRange(1.0,10.0)
        self.heightSpin.setDecimals(1)
        self.heightSpin.setSingleStep(0.5)
        propertiesLayout = QHBoxLayout(self.propertiesWidget)
        propertiesLayout.setContentsMargins(0,0,0,0)
        for widget in (self.widthLabel, self.widthSpin, self.heightLabel, self.heightSpin):
            propertiesLayout.addWidget(widget)
        propertiesLayout.addStretch()
        # border properties
        self.borderLabel = QLabel("Border :", self.propertiesWidget)
        self.borderWidthSpin = QDoubleSpinBox(self.propertiesWidget)
        self.borderWidthSpin.setRange(0.3, 3.0)
        self.borderWidthSpin.setDecimals(1)
        self.borderWidthSpin.setSingleStep(0.1)
        self.borderWidthSpin.setSuffix(" mm")
        self.roundedBorderBtn = QCheckBox("Rounded Corner", self.propertiesWidget)
        for widget in (self.borderLabel, self.borderWidthSpin, self.roundedBorderBtn):
            propertiesLayout.addWidget(widget)
        # fonts
        self.fontWidget = QWidget(self)
        self.fontLabel = QLabel("Font :", self.fontWidget)
        self.headingFontCombo = QFontComboBox(self.fontWidget)
        self.bodyFontCombo = QFontComboBox(self.fontWidget)
        fontLayout = QHBoxLayout(self.fontWidget)
        fontLayout.setContentsMargins(0,0,0,0)
        for widget in (self.fontLabel, self.headingFontCombo, self.bodyFontCombo):
            fontLayout.addWidget(widget)
        self.fontWidget.setVisible(False)
        # create contents widget
        self.contentsWidget = QWidget(self)
        self.structureFileEdit = QLineEdit(self)
        self.structureFileEdit.setPlaceholderText("Structure / Image")
        self.structureFileEdit.setReadOnly(True)
        self.structureChooserBtn = QPushButton("Choose", self)
        self.headingEdit = QLineEdit(self)
        self.headingEdit.setPlaceholderText("Heading / Formula")
        self.headingFormulaBtn = QCheckBox("Formula", self)
        self.headingFormulaBtn.setChecked(True)
        self.bodyEdit = QLineEdit(self)
        self.bodyEdit.setPlaceholderText("Body / Formula")
        self.bodyFormulaBtn = QCheckBox("Formula", self)
        contentsLayout = QGridLayout(self.contentsWidget)
        for i,widget in enumerate([self.structureFileEdit, self.structureChooserBtn,
            self.headingEdit, self.headingFormulaBtn, self.bodyEdit, self.bodyFormulaBtn]):
                contentsLayout.addWidget(widget, i//2, i%2, 1, 1)
        # hazard symbols
        self.hazardWidget = QWidget(self)
        hazardLayout = QHBoxLayout(self.hazardWidget)
        hazardLayout.setContentsMargins(0,0,0,0)
        #hazardLayout.addStretch()
        ghs_symbols = ["Explosive", "Flammable", "Oxidising", "Corrosive",
                    "Toxic", "Irritant", "Health-Hazard", "Environmental-Hazard"]
        self.ghs_btns = {}
        for symbol in ghs_symbols:
            btn = QToolButton(self.hazardWidget)
            btn.setCheckable(True)
            btn.setToolTip(symbol)
            btn.setIconSize(QSize(32,32))
            btn.setIcon(QIcon(":/hazard-symbols/%s.png"%symbol.lower()))
            hazardLayout.addWidget(btn)
            self.ghs_btns[symbol] = btn
        hazardLayout.addStretch()
        # others
        self.settingsBtn = QToolButton(self)
        self.settingsBtn.setCheckable(True)
        self.settingsBtn.setIconSize(QSize(24,24))
        self.settingsBtn.setIcon(QIcon(":/icons/settings.png"))
        hazardLayout.addWidget(self.settingsBtn)
        self.btnBox = QDialogButtonBox(QDialogButtonBox.Cancel, parent=self)
        self.btnBox.addButton("Add", QDialogButtonBox.AcceptRole)
        self.preview = QLabel(self)
        # layout widgets
        layout.addWidget(self.propertiesWidget, 0,0,1,2)
        layout.addWidget(self.preview, 1,0,1,1)
        layout.addWidget(self.contentsWidget, 1,1,1,1)
        layout.addWidget(self.hazardWidget, 2,0,1,2)
        layout.addWidget(self.fontWidget, 3,0,1,2)
        layout.addWidget(self.btnBox, 4,0,1,2)
        # connect signals
        for spinbox in (self.widthSpin, self.heightSpin, self.borderWidthSpin):
            spinbox.valueChanged.connect(self.showPreview)
        self.roundedBorderBtn.clicked.connect(self.showPreview)
        self.headingFontCombo.currentFontChanged.connect(self.showPreview)
        self.bodyFontCombo.currentFontChanged.connect(self.showPreview)
        self.structureChooserBtn.clicked.connect(self.chooseStructure)
        self.headingFormulaBtn.clicked.connect(self.setHeadingFormula)
        self.bodyFormulaBtn.clicked.connect(self.setSubheadingFormula)
        self.headingEdit.textEdited.connect(self.onTextEdit)
        self.bodyEdit.textEdited.connect(self.showPreview)
        for btn in self.ghs_btns.values():
            btn.clicked.connect(self.showPreview)
        self.settingsBtn.clicked.connect(self.toggleSettings)
        self.btnBox.accepted.connect(self.accept)
        self.btnBox.rejected.connect(self.reject)
        # initialize values
        self.items = []
        self.structure = None

        self.headingEdit.setFocus()
        self.showPreview()

    def getValues(self):
        w = self.widthSpin.value()
        h = self.heightSpin.value()
        border_w = self.borderWidthSpin.value()
        rounded = self.roundedBorderBtn.isChecked()
        h_font = self.headingFontCombo.currentFont()
        b_font = self.bodyFontCombo.currentFont()
        return (w,h), border_w, rounded, (h_font, b_font)

    def setValues(self, size, border_w, rounded, fonts=None):
        self.widthSpin.setValue(size[0])
        self.heightSpin.setValue(size[1])
        self.borderWidthSpin.setValue(border_w)
        self.roundedBorderBtn.setChecked(rounded)
        if fonts:
            self.headingFontCombo.setCurrentFont(fonts[0])
            self.bodyFontCombo.setCurrentFont(fonts[1])


    def accept(self):
        """ do not close dialog if empty """
        if self.headingEdit.text() or self.bodyEdit.text():
            QDialog.accept(self)

    def chooseStructure(self):
        filename, filtr = QFileDialog.getOpenFileName(self, "Choose Image", None,
                        "Image Files (*.png *.jpg *.jpeg *.webp)")
        if not filename:
            return False
        #self.structure_filename = filename
        self.structure = QPixmap(filename)
        self.structureFileEdit.setText(os.path.basename(filename))
        self.showPreview()

    def setHeadingFormula(self, checked):
        if checked:
            self.bodyFormulaBtn.setChecked(False)
        self.showPreview()

    def setSubheadingFormula(self, checked):
        if checked:
            self.headingFormulaBtn.setChecked(False)
        self.showPreview()

    def onTextEdit(self):
        self.showPreview()

    def toggleSettings(self, checked):
        self.fontWidget.setVisible(checked)

    def get_selected_GHS_symbols(self):
        selected = []
        for name, btn in self.ghs_btns.items():
            if btn.isChecked():
                selected.append(name.lower())
        return selected

    def showPreview(self):
        formula = None
        heading = self.headingEdit.text()
        body = self.bodyEdit.text()
        w = int(round(self.widthSpin.value()/0.0254)) # cm to px @100 dpi
        h = int(round(self.heightSpin.value()/0.0254)) # cm to px @100 dpi
        border_w = self.borderWidthSpin.value()/0.254 # mm to px @100 dpi
        cont_w = w - 2*border_w # text contents width
        cont_h = h - 2*border_w
        # generate textitems and calculate size
        # background
        rect = border_w/2, border_w/2, w-border_w, h-border_w
        path = QPainterPath()
        if self.roundedBorderBtn.isChecked():
            path.addRoundedRect(*rect, 15,15)
        else:
            path.addRect(*rect)
        bg = QGraphicsPathItem(path)
        pen = QPen(Qt.black, border_w)
        pen.setJoinStyle(Qt.MiterJoin)# sharp corner
        bg.setPen(pen)
        bg.setBrush(Qt.white)
        # structure image and ghs pictograms
        structure_h = cont_h//3 if self.structure else 0
        ghs_symbols = self.get_selected_GHS_symbols()
        ghs_h = cont_h//4 if ghs_symbols else 0
        # text area
        txt_area_w = cont_w
        txt_area_h = cont_h - structure_h - ghs_h
        self.items = []
        if self.structure:
            item = QGraphicsPixmapItem(self.structure)
            item.setTransformationMode(Qt.SmoothTransformation)
            item.setScale(structure_h/self.structure.height())
            item.moveBy(border_w + (cont_w - item.sceneBoundingRect().width())/2, 0)# align center
            self.items.append(item)
        if heading:
            content = to_html(heading, self.headingFormulaBtn.isChecked())
            font = self.headingFontCombo.currentFont()
            item = get_text_item(content, w, font, int(txt_area_h//3))
            self.items.append(item)
        if body:
            content = to_html(body, self.bodyFormulaBtn.isChecked())
            font = self.bodyFontCombo.currentFont()
            # body font must be smaller than heading font
            font_size = min(item.font().pixelSize()-1, txt_area_h//6) if heading else txt_area_h//6
            item = get_text_item(content, w, font, int(font_size))
            self.items.append(item)
        if ghs_symbols:
            pms = [QPixmap(":/hazard-symbols/%s.png"%sym) for sym in ghs_symbols]
            l = pms[0].width()
            ghs_pm = QPixmap(l*len(ghs_symbols), l)
            ghs_pm.fill(Qt.transparent)
            painter = QPainter(ghs_pm)
            for i, pm in enumerate(pms):
                painter.drawPixmap(i*l, 0, pm)
            painter.end()
            item = QGraphicsPixmapItem(ghs_pm)
            item.setTransformationMode(Qt.SmoothTransformation)
            item.setScale(ghs_h/ghs_pm.height())
            item.moveBy(border_w + (cont_w - item.sceneBoundingRect().width())/2, 0)
            self.items.append(item)
        # draw
        heights = [item.sceneBoundingRect().height() for item in self.items]
        total_h = reduce(operator.add, heights, 0)
        spacing = (cont_h-total_h)//(len(self.items)+1)
        pm = QPixmap(w,h)
        pm.fill()
        painter = QPainter(pm)
        #painter.setRenderHint(QPainter.Antialiasing)
        opt = QStyleOptionGraphicsItem()
        bg.paint(painter, opt, None)
        y = border_w + spacing
        for item in self.items:
            item.moveBy(0,y)
            painter.setTransform(item.sceneTransform(), True)
            item.paint(painter, opt, None)
            painter.resetTransform()
            y += item.sceneBoundingRect().height() + spacing
        painter.end()
        self.items.insert(0, bg)

        if pm.width()>200 or pm.height()>100:
            pm = pm.scaled(200,100,Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.preview.setPixmap(pm)
        self.label_size = w, h


    def getLabel(self):
        label = Label(self.label_size)
        label.items = self.items
        return label


def get_text_item(text, width, font, font_size):
    doc = QTextDocument()
    doc.setHtml(text)
    doc.setTextWidth(width) # for center alignment or wrapping
    text_option = QTextOption(Qt.AlignVCenter|Qt.AlignHCenter)
    text_option.setWrapMode(QTextOption.NoWrap)
    doc.setDefaultTextOption(text_option)
    font.setPixelSize(font_size)
    doc.setDefaultFont(font)
    orig_font_size = font_size
    while doc.idealWidth() > width or line_count(doc)>2:
        font_size -= 1
        if font_size < 0.8*orig_font_size:
            text_option.setWrapMode(QTextOption.WordWrap)
            doc.setDefaultTextOption(text_option)
        font.setPixelSize(font_size)
        doc.setDefaultFont(font)
    item = QGraphicsTextItem()
    item.setDocument(doc)
    return item

def line_count(doc):
    """ returns actual visible line count in QTextDocument after word wrapping """
    total_lines = 0
    # Iterate through each paragraph (block)
    block = doc.begin()
    while block.isValid():
        # Ensure the layout exists
        layout = block.layout()
        if layout:
            total_lines += layout.lineCount()
        block = block.next()

    return total_lines

# [( subscript numbers next to alphabet or bracket
formula_num_re = "([A-Za-z)\]])(\d+)"

def subscript(match):
    return match.group(1) + "<sub>" + match.group(2) + "</sub>"

# converts H2O to H<sub>2</sub>O
def to_html(text, formula=False):
    if formula:
        return re.sub(formula_num_re, subscript, text)
    return text


def drawHtmlText(text):
    # 1. Prepare the Pixmap
    pixmap = QPixmap(400, 200)
    pixmap.fill(Qt.white) # Ensure a clean background

    # 2. Setup the HTML Document
    doc = QTextDocument()
    doc.setHtml(html_content)
    doc.setTextWidth(pixmap.width()) # Optional: constrain width for wrapping

    # 3. Draw onto the Pixmap
    painter = QPainter(pixmap)
    doc.drawContents(painter)
    painter.end()



import sys
from PyQt5.QtWidgets import QApplication
import resources_rc


if __name__ == "__main__":
    app = QApplication(sys.argv)
    dlg = LabelPrintDialog()
    dlg.show()
    sys.exit(app.exec())
