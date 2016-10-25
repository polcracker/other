#!/usr/bin/env python
# -*- coding: utf8 -*-
from PyQt4 import QtGui, QtCore
from PyQt4.QtCore import Qt

from config import VERSION
from lib.resourcedialog import CResourceDialog
from lib.tablemodel import CTableModel
from lib.taskdialog import CTaskDialog
from lib.threadqueue import CThreadQueue
from lib.utils import setResources
from logic.planning import Processor, createProcess
from logic.threadroutines import routine_1
from threading import Event
from ui.ui_taskmanager import Ui_MainDialog


class CTaskManager(QtGui.QDialog, Ui_MainDialog):
    def __init__(self, processorCount=2):
        # initialize ui
        QtGui.QDialog.__init__(self)
        Ui_MainDialog.__init__(self)
        self.setupUi(self)
        self.setWindowFlags(Qt.WindowSystemMenuHint | Qt.WindowTitleHint)
        self.setWindowIcon(QtGui.QIcon('favicon.ico'))
        self.setWindowTitle('Taskprocessor %s' % VERSION)

        self.tblModel = CTableModel(self)
        # self.tblProxyModel = QtGui.QSortFilterProxyModel(self)
        # self.tblProxyModel.setSourceModel(self.tblModel)

        self.tblTask.setModel(self.tblModel)  # tblProxyModel)
        self.tblTask.verticalHeader().setVisible(True)

        # self.tblTask.resizeColumnsToContents()
        self.tblTask.autoFillBackground()
        self.tblTask.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.tblTask.horizontalHeader().setDefaultAlignment(QtCore.Qt.AlignCenter)
        # self.tblTask.row
        self.tblTask.setAlternatingRowColors(True)

        for col in xrange(self.tblTask.model().columnCount()):
            if col == 0:
                self.tblTask.horizontalHeader().resizeSection(col, 500)
                self.tblTask.horizontalHeader().setResizeMode(col, QtGui.QHeaderView.Stretch)
            elif col == 1:
                self.tblTask.horizontalHeader().resizeSection(col, 90)
                self.tblTask.horizontalHeader().setResizeMode(col, QtGui.QHeaderView.Custom)
            elif col == 2:
                self.tblTask.horizontalHeader().resizeSection(col, 80)
                self.tblTask.horizontalHeader().setResizeMode(col, QtGui.QHeaderView.Custom)
            elif col == 3:
                self.tblTask.horizontalHeader().resizeSection(col, 65)
                self.tblTask.horizontalHeader().setResizeMode(col, QtGui.QHeaderView.Custom)
            elif col == 4:
                self.tblTask.horizontalHeader().resizeSection(col, 120)
                self.tblTask.horizontalHeader().setResizeMode(col, QtGui.QHeaderView.Custom)


        self.taskIndex = 0

        self.queue = CThreadQueue()
        self.sjfNewThreadEvent = Event()

        self.processorsList = []
        for x in range(processorCount):
            self.processorsList.append(Processor(self.queue, self.sjfNewThreadEvent))
            self.processorsList[x].suspended = self.chkPauseAll.isChecked()
            self.processorsList[x].name = self.processorsList[x].name % x
            self.processorsList[x].start()

        self.resources = CResourceDialog(None)

    @QtCore.pyqtSlot(bool)
    def on_chkPauseAll_toggled(self, checked):
        if checked:
            for x in self.processorsList:
                x.suspendCurrentThread()
        else:
            for x in self.processorsList:
                x.resumeCurrentThread()
        # self.tblTask.model().layoutChanged.emit()

    @QtCore.pyqtSlot()
    def on_btnNewTask_clicked(self):
        dlg = CTaskDialog(self)
        # dlg.setResources(self.resources.resourceList)
        if dlg.exec_():
            x = createProcess(
                dlg.edtTaskName.text(),
                routine_1,
                dlg.cmbTaskPriority.currentIndex(),
                dlg.spbTaskTime.value(),
                [x.text() for x in dlg.lstAvailableResources.selectedItems()]
            )
            # self.processor.queue.push(x)
            # self.processor.startPlanning()
            self.queue.push(x)
            self.queue.startPlanning()
            # self.processor.startPlanning()
            if not self.sjfNewThreadEvent.isSet():
                self.sjfNewThreadEvent.set()
            # self.processor.allThreads.append(x)
            self.tblTask.model().body = self.queue.data  # self.processor.queue.data
            self.tblTask.model().layoutChanged.emit()
            # self.tblTask.resizeColumnsToContents()
            self.taskIndex += 1

            self.setResources(self.queue.data)  # self.processor.queue.data)
        del dlg

    @QtCore.pyqtSlot()
    def on_btnResourceTable_clicked(self):
        self.setResources(self.queue.data)  # self.processor.queue.data)
        self.resources.exec_()

    @QtCore.pyqtSlot()
    def on_btnClearFinished_clicked(self):
        self.queue.removeFinished()
        self.setResources(self.queue.data)
        self.tblTask.model().body = self.queue.data  # self.processor.queue.data
        self.tblTask.model().layoutChanged.emit()

    def setResources(self, process=list()):
        setResources(None, self.lstUsefullResources, process[::-1])

    def closeEvent(self, event):
        for x in self.processorsList:
            x.enable = False

            if x.suspended:
                x.resumeCurrentThread()
            elif not self.sjfNewThreadEvent.isSet():
                self.sjfNewThreadEvent.set()

        event.accept()
