# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SurvexImport
                                 A QGIS plugin
 Import features from survex .3d files
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2019-05-03
        git sha              : $Format:%H$
        copyright            : (C) 2019-2020 by Patrick B Warren
        email                : patrickbwarren@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from PyQt5.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
from PyQt5.QtCore import QFileInfo, QDate, QVariant
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QAction, QFileDialog

from qgis.core import Qgis
from qgis.core import QgsProject, QgsVectorLayer, QgsField, QgsFeature, QgsGeometry
from qgis.core import QgsPoint, QgsLineString, QgsPolygon
from qgis.core import QgsVectorFileWriter, QgsMessageLog
from qgis.core import QgsCoordinateReferenceSystem
from qgis.gui import QgsProjectionSelectionDialog

# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .survex_import_dialog import SurvexImportDialog

from struct import unpack # used to read binary from .3d file
from re import search # for matching and extracting substrings
from math import log10, floor, sqrt

import os # used for file system operations

from osgeo import osr # spatial reference system API

class SurvexImport:
    """QGIS Plugin Implementation."""

    # The following are some dictionaries for flags in the .3d file

    station_attr = {0x01:'SURFACE', 0x02:'UNDERGROUND', 0x04:'ENTRANCE',
                    0x08:'EXPORTED', 0x10:'FIXED', 0x20:'ANON'}

    leg_attr = {0x01:'SURFACE', 0x02:'DUPLICATE', 0x04:'SPLAY'}

    style_type = {0x00:'NORMAL', 0x01:'DIVING', 0x02:'CARTESIAN',
                  0x03:'CYLPOLAR', 0x04:'NOSURVEY', 0xff:'NOSTYLE'}

    # lists of keys of above, sorted to restore ordering

    station_flags = sorted(station_attr.keys())
    leg_flags = sorted(leg_attr.keys())

    # field names if there is error data

    error_fields = ('ERROR_VERT', 'ERROR_HORIZ', 'ERROR', 'LENGTH')

    # main data structures

    leg_list = [] # accumulates legs + metadata
    station_list = [] # ditto stations
    xsect_list = [] # ditto for cross sections for walls

    station_xyz = {} # map station names to xyz coordinates

    crs = None # used to set layer CRS in memory provider
    crs_source = None # records the origin of the CRS
    title = '' # used to set layer title in memory provider

    path_3d = '' # to remember the path to the survex .3d file
    path_gpkg = '' # ditto for path to save GeoPackage (.gpkg)

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'SurvexImport_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Import .3d file')

        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.first_start = None

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('SurvexImport', message)

    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToVectorMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/survex_import/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'.3d import'),
            callback=self.run,
            parent=self.iface.mainWindow())

        # will be set False in run()
        self.first_start = True

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginVectorMenu(
                self.tr(u'&Import .3d file'),
                action)
            self.iface.removeToolBarIcon(action)

    def crs_from_file(self):
        """Enforce consistent CRS selector state"""
        if self.dlg.CRSFromFile.isChecked():
            self.dlg.CRSFromProject.setChecked(False)

    def crs_from_project(self):
        """Enforce consistent CRS selector state"""
        if self.dlg.CRSFromProject.isChecked():
            self.dlg.CRSFromFile.setChecked(False)

    def select_3d_file(self):
        """Select 3d file"""
        file_3d, _filter_3d = QFileDialog.getOpenFileName(self.dlg, "Select .3d file ", self.path_3d, '*.3d')
        self.dlg.selectedFile.setText(file_3d)
        self.path_3d = QFileInfo(file_3d).path() # memorise path selection

    def select_gpkg(self):
        """Select GeoPackage (.gpkg)"""
        file_gpkg, _filter_gpkg = QFileDialog.getSaveFileName(self.dlg, "Enter or select existing .gpkg file ",
                                                              self.path_gpkg, '*.gpkg')
        self.dlg.selectedGPKG.setText(file_gpkg)
        self.path_gpkg = QFileInfo(file_gpkg).path() # memorise path selection

    def set_crs(self, s):
        """Figure out the CRS for layer creation, from the selected options and/or string"""
        if self.dlg.CRSFromProject.isChecked():
            self.crs_source = 'from project'
            self.crs = QgsProject.instance().crs()
        elif self.dlg.CRSFromFile.isChecked() and s:
            self.crs_source = 'from .3d file'
            self.crs = QgsCoordinateReferenceSystem()
            match = search('epsg:([0-9]*)', s) # check for epsg in proj string
            if match: # if found, use the EPSG number explicitly
                self.crs.createFromString('EPSG:{}'.format(int(match.group(1))))
            else: # fall back to proj4
                self.crs.createFromProj4(s)
        else: # fall back to raising a CRS selection dialog
            self.crs_source = 'from dialog'
            dialog = QgsProjectionSelectionDialog()
            dialog.setMessage('define the CRS for the imported layers')
            dialog.exec() # run the dialog ..
            self.crs = dialog.crs() # .. and recover the user input
        if self.crs.isValid():
            msg = 'CRS {} : {}'.format(self.crs_source, self.crs.authid())
            QgsMessageLog.logMessage(msg, tag='Import .3d', level=Qgis.Info)
            QgsMessageLog.logMessage(self.crs.description(), tag='Import .3d', level=Qgis.Info)
        else: # hopefully never happens
            msg = "CRS invalid!"
            QgsMessageLog.logMessage(msg, tag='Import .3d', level=Qgis.Info)
            self.crs = None

    def all_checked(self):
        """ ensures the import all check box is consistent"""
        check = self.dlg.Legs.isChecked()
        check = check and self.dlg.Stations.isChecked()
        check = check and self.dlg.Polygons.isChecked() 
        check = check and self.dlg.Walls.isChecked()
        check = check and self.dlg.XSections.isChecked()
        check = check and self.dlg.Traverses.isChecked()
        check = check and self.dlg.LegsSurface.isChecked()
        check = check and self.dlg.LegsSplay.isChecked()
        check = check and self.dlg.LegsDuplicate.isChecked()
        check = check and self.dlg.StationsSurface.isChecked()
        self.dlg.ImportAll.setChecked(check)

    def toggle_import_all(self):
        """toggle import all possible data"""
        checked = self.dlg.ImportAll.isChecked()
        self.dlg.Legs.setChecked(checked)
        self.dlg.Stations.setChecked(checked)
        self.dlg.Polygons.setChecked(checked) 
        self.dlg.Walls.setChecked(checked)
        self.dlg.XSections.setChecked(checked)
        self.dlg.Traverses.setChecked(checked)
        self.dlg.LegsSurface.setChecked(checked)
        self.dlg.LegsSplay.setChecked(checked)
        self.dlg.LegsDuplicate.setChecked(checked)
        self.dlg.StationsSurface.setChecked(checked)

    def add_layer(self, subtitle, geom):
        """Add a memory layer with title(subtitle) and geom"""
        name = '%s(%s)' % (self.title, subtitle) if self.title else subtitle
        layer =  QgsVectorLayer(geom, name, 'memory')
        if self.crs: # this should have been set by now
            layer.setCrs(self.crs)
        if not layer.isValid():
            raise Exception("Invalid layer with %s" % geom)
        msg = "Memory layer '%s' called '%s' added" % (geom, name)
        QgsMessageLog.logMessage(msg, tag='Import .3d', level=Qgis.Info)
        return layer

# The next three routines are to do with reading .3d binary file format

    def read_xyz(self, fp):
        """Read xyz as integers, according to .3d spec"""
        return unpack('<iii', fp.read(12))

    def read_len(self, fp):
        """Read a number as a length according to .3d spec"""
        byte = ord(fp.read(1))
        if byte != 0xff:
            return byte
        else:
            return unpack('<I', fp.read(4))[0]

    def read_label(self, fp, current_label):
        """Read a string as a label, or part thereof, according to .3d spec"""
        byte = ord(fp.read(1))
        if byte != 0x00:
            ndel = byte >> 4
            nadd = byte & 0x0f
        else:
            ndel = self.read_len(fp)
            nadd = self.read_len(fp)
        oldlen = len(current_label)
        return current_label[:oldlen - ndel] + fp.read(nadd).decode('ascii')

    def run(self):
        """Run method that performs all the real work"""

        # Create the dialog with elements (after translation) and keep reference
        # Only create GUI ONCE in callback, so that it will only load when the plugin is started

        if self.first_start == True:
            self.first_start = False
            self.dlg = SurvexImportDialog()
            self.dlg.selectedFile.clear()
            self.dlg.fileSelector.clicked.connect(self.select_3d_file)
            self.dlg.selectedGPKG.clear()
            self.dlg.GPKGSelector.clicked.connect(self.select_gpkg)
            self.dlg.CRSFromProject.setChecked(False)
            self.dlg.CRSFromFile.clicked.connect(self.crs_from_file)
            self.dlg.CRSFromFile.setChecked(False)
            self.dlg.CRSFromProject.clicked.connect(self.crs_from_project)
            self.dlg.ImportAll.clicked.connect(self.toggle_import_all)
            self.dlg.Legs.clicked.connect(self.all_checked)
            self.dlg.Stations.clicked.connect(self.all_checked)
            self.dlg.Polygons.clicked.connect(self.all_checked)
            self.dlg.Walls.clicked.connect(self.all_checked)
            self.dlg.XSections.clicked.connect(self.all_checked)
            self.dlg.Traverses.clicked.connect(self.all_checked)
            self.dlg.LegsSurface.clicked.connect(self.all_checked)
            self.dlg.LegsSplay.clicked.connect(self.all_checked)
            self.dlg.LegsDuplicate.clicked.connect(self.all_checked)
            self.dlg.StationsSurface.clicked.connect(self.all_checked)

        self.dlg.show() # show the dialog

        result = self.dlg.exec_() # Run the dialog event loop

        if result:  # The user pressed OK, and this is what happened next!

            survex_3d = self.dlg.selectedFile.text()
            gpkg_file = self.dlg.selectedGPKG.text()

            include_legs = self.dlg.Legs.isChecked()
            include_stations = self.dlg.Stations.isChecked()
            include_polygons = self.dlg.Polygons.isChecked()
            include_walls = self.dlg.Walls.isChecked()
            include_xsections = self.dlg.XSections.isChecked()
            include_traverses = self.dlg.Traverses.isChecked()

            exclude_surface_legs = not self.dlg.LegsSurface.isChecked()
            exclude_splay_legs = not self.dlg.LegsSplay.isChecked()
            exclude_duplicate_legs = not self.dlg.LegsDuplicate.isChecked()

            exclude_surface_stations = not self.dlg.StationsSurface.isChecked()

            use_clino_wgt = self.dlg.UseClinoWeights.isChecked()
            include_up_down = self.dlg.IncludeUpDown.isChecked()

            discard_features = not self.dlg.KeepFeatures.isChecked()

            if not os.path.exists(survex_3d):
                raise Exception("File '%s' doesn't exist" % survex_3d)

            if discard_features:
                self.leg_list = []
                self.station_list = []
                self.station_xyz = {}
                self.xsect_list = []

            # Read .3d file as binary, parse, and save data structures

            with open(survex_3d, 'rb') as fp:

                line = fp.readline().rstrip() # File ID check

                if not line.startswith(b'Survex 3D Image File'):
                    raise IOError('Not a survex .3d file: ' + survex_3d)

                line = fp.readline().rstrip() # File format version

                if not line.startswith(b'v'):
                    raise IOError('Unrecognised survex .3d version in ' + survex_3d)

                version = int(line[1:])
                if version < 8:
                    raise IOError('Survex .3d version >= 8 required in ' + survex_3d)

                line = fp.readline().rstrip() # Metadata (title and coordinate system)
                fields = line.split(b'\x00')

                previous_title = '' if discard_features else self.title

                if previous_title:
                    self.title = previous_title + ' + ' + fields[0].decode('ascii');
                else:
                    self.title = fields[0].decode('ascii');

                self.set_crs(fields[1].decode('ascii') if len(fields) > 1 else None)

                line = fp.readline().rstrip() # Timestamp, unused in present application

                if not line.startswith(b'@'):
                    raise IOError('Unrecognised timestamp in ' + survex_3d)

                # timestamp = int(line[1:])

                flag = ord(fp.read(1)) # file-wide flag

                if flag & 0x80: # abort if extended elevation
                    raise IOError("Can't deal with extended elevation in " + survex_3d)

                # All file-wide header data read in, now read byte-wise
                # according to .3d spec.  Note that all elements must
                # be processed, in order, otherwise we get out of sync.

                # We first define some baseline dates

                date0 = QDate(1900, 1, 1)
                date1 = QDate(1900, 1, 1)
                date2 = QDate(1900, 1, 1)

                label, style = '', 0xff # initialise label and style

                legs = [] # will be used to capture leg data between MOVEs
                xsect = [] # will be used to capture XSECT data
                nlehv = None # .. remains None if there isn't any error data...

                while True: # start of byte-gobbling while loop

                    char = fp.read(1)

                    if not char: # End of file (reached prematurely?)
                        raise IOError('Premature end of file in ' + survex_3d)

                    byte = ord(char)

                    if byte <= 0x05: # STYLE
                        if byte == 0x00 and style == 0x00: # this signals end of data
                            if legs: # there may be a pending list of legs to save
                                self.leg_list.append((legs,  nlehv))
                            break # escape from byte-gobbling while loop
                        else:
                            style = byte

                    elif byte <= 0x0e: # Reserved
                        continue

                    elif byte == 0x0f: # MOVE
                        xyz = self.read_xyz(fp)
                        if legs:
                            self.leg_list.append((legs,  nlehv))
                            legs = []

                    elif byte == 0x10: # DATE (none)
                        date1 = date2 = date0

                    elif byte == 0x11: # DATE (single date)
                        days = unpack('<H', fp.read(2))[0]
                        date1 = date2 = date0.addDays(days)

                    elif byte == 0x12:  # DATE (date range, short format)
                        days, extra = unpack('<HB', fp.read(3))
                        date1 = date0.addDays(days)
                        date2 = date0.addDays(days + extra + 1)

                    elif byte == 0x13: # DATE (date range, long format)
                        days1, days2 = unpack('<HH', fp.read(4))
                        date1 = date0.addDays(days1)
                        date2 = date0.addDays(days2)

                    elif byte <= 0x1e: # Reserved
                        continue

                    elif byte == 0x1f:  # Error info
                        nlehv = unpack('<iiiii', fp.read(20))

                    elif byte <= 0x2f: # Reserved
                        continue

                    elif byte <= 0x33: # XSECT
                        label = self.read_label(fp, label)
                        if byte & 0x02:
                            lrud = unpack('<iiii', fp.read(16))
                        else:
                            lrud = unpack('<hhhh', fp.read(8))
                        xsect.append((label, lrud))
                        if byte & 0x01: # XSECT_END
                            self.xsect_list.append(xsect)
                            xsect = []

                    elif byte <= 0x3f: # Reserved
                        continue

                    elif byte <= 0x7f: # LINE
                        flag = byte & 0x3f
                        if not (flag & 0x20):
                            label = self.read_label(fp, label)
                        xyz_prev = xyz
                        xyz = self.read_xyz(fp)
                        while (True): # code pattern to implement logic
                            if exclude_surface_legs and flag & 0x01: break
                            if exclude_duplicate_legs and flag & 0x02: break
                            if exclude_splay_legs and flag & 0x04: break
                            legs.append(((xyz_prev, xyz), label, style, date1, date2, flag))
                            break

                    elif byte <= 0xff: # LABEL (or NODE)
                        flag = byte & 0x7f
                        label = self.read_label(fp, label)
                        xyz = self.read_xyz(fp)
                        while (True): # code pattern to implement logic
                            if exclude_surface_stations and flag & 0x01 and not flag & 0x02: break
                            self.station_list.append((xyz, label, flag))
                            break
                        self.station_xyz[label] = xyz

                # End of byte-gobbling while loop

            # file closes automatically, with open(survex_3d, 'rb') as fp:

            layers = [] # used to keep a list of the created layers

            if include_stations and self.station_list: # station layer

                station_layer = self.add_layer('stations', 'PointZ')

                attrs = [QgsField(self.station_attr[k], QVariant.Int) for k in self.station_flags]
                attrs.insert(0, QgsField('ELEVATION', QVariant.Double))
                attrs.insert(0, QgsField('NAME', QVariant.String))
                station_layer.dataProvider().addAttributes(attrs)
                station_layer.updateFields()

                features = []

                for (xyz, label, flag) in self.station_list:
                    xyz = [0.01*v for v in xyz]
                    attrs = [1 if flag & k else 0 for k in self.station_flags]
                    attrs.insert(0, round(xyz[2], 2)) # elevation
                    attrs.insert(0, label)
                    feat = QgsFeature()
                    geom = QgsGeometry(QgsPoint(*xyz))
                    feat.setGeometry(geom)
                    feat.setAttributes(attrs)
                    features.append(feat)

                station_layer.dataProvider().addFeatures(features)
                layers.append(station_layer)

            if include_legs and self.leg_list: # leg layer

                leg_layer = self.add_layer('legs', 'LineStringZ')

                attrs = [QgsField(self.leg_attr[k], QVariant.Int) for k in self.leg_flags]
                if nlehv:
                    [ attrs.insert(0, QgsField(s, QVariant.Double)) for s in self.error_fields ]
                    attrs.insert(0, QgsField('NLEGS', QVariant.Int))
                attrs.insert(0, QgsField('DATE2', QVariant.Date))
                attrs.insert(0, QgsField('DATE1', QVariant.Date))
                attrs.insert(0, QgsField('STYLE', QVariant.String))
                attrs.insert(0, QgsField('ELEVATION', QVariant.Double))
                attrs.insert(0, QgsField('NAME', QVariant.String))
                leg_layer.dataProvider().addAttributes(attrs)
                leg_layer.updateFields()

                features = []

                for legs, nlehv in self.leg_list:
                    for (xyz_pair, label, style, from_date, to_date, flag) in legs:
                        elev = 0.5 * sum([0.01*xyz[2] for xyz in xyz_pair])
                        points = []
                        for xyz in xyz_pair:
                            xyz = [0.01*v for v in xyz]
                            points.append(QgsPoint(*xyz))
                        attrs = [1 if flag & k else 0 for k in self.leg_flags]
                        if nlehv:
                            [ attrs.insert(0, 0.01*v) for v in reversed(nlehv[1:5]) ]
                            attrs.insert(0, nlehv[0])
                        attrs.insert(0, to_date)
                        attrs.insert(0, from_date)
                        attrs.insert(0, self.style_type[style])
                        attrs.insert(0, round(elev, 2))
                        attrs.insert(0, label)
                        linestring = QgsLineString()
                        linestring.setPoints(points)
                        feat = QgsFeature()
                        geom = QgsGeometry(linestring)
                        feat.setGeometry(geom)
                        feat.setAttributes(attrs)
                        features.append(feat)

                leg_layer.dataProvider().addFeatures(features)
                layers.append(leg_layer)

            # Now do wall features if asked

            if (include_traverses or include_xsections
                or include_walls or include_polygons) and self.xsect_list:

                trav_features = []
                wall_features = []
                xsect_features = []
                quad_features = []

                for xsect in self.xsect_list:

                    if len(xsect) < 2: # if there's only one station ..
                        continue # .. give up as we don't know which way to face

                    centerline = [] # will contain the station position and LRUD data

                    for label, lrud in xsect:
                        xyz = self.station_xyz[label] # look up coordinates from label
                        lrud_or_zero = tuple([max(0, v) for v in lrud]) # deal with missing data
                        centerline.append(xyz + lrud_or_zero) # and collect as 7-uple

                    direction = [] # will contain the corresponding direction vectors

                    # The calculations below use integers for xyz and lrud, and
                    # conversion to metres is left to the end.  Then dh2 is an
                    # integer and the test for a plumb is safely dh2 = 0.

                    # The directions are unit vectors optionally weighted by
                    # cos(inclination) = dh/dl where dh^2 = dx^2 + dy^2 (note, no dz^2),
                    # and dl^2 = dh^2 + dz^2.  The normalisation is correspondingly
                    # either 1/dh, or 1/dh * dh/dl = 1/dl.

                    for i, xyzlrud in enumerate(centerline):
                        x, y, z = xyzlrud[0:3]
                        if i > 0:
                            dx, dy, dz = x - xp, y - yp, z - zp
                            dh2 = dx*dx + dy*dy # integer horizontal displacement (mm^2)
                            norm = sqrt(dh2 + dz*dz) if use_clino_wgt else sqrt(dh2)
                            dx, dy = (dx/norm, dy/norm) if dh2 > 0 and norm > 0 else (0, 0)
                            direction.append((dx, dy))
                        xp, yp, zp = x, y, z

                    left_wall = []
                    right_wall = []
                    up_down = []

                    # We build the walls by walking through the list
                    # of stations and directions, with simple defaults
                    # for the start and end stations

                    for i, (x, y, z, l, r, u, d) in enumerate(centerline):
                        d1x, d1y = direction[i-1] if i > 0 else (0, 0)
                        d2x, d2y = direction[i] if i+1 < len(centerline) else (0, 0)
                        dx, dy = d1x+d2x, d1y+d2y # mean (sum of) direction vectors
                        norm = sqrt(dx*dx + dy*dy) # normalise to unit vector
                        ex, ey = (dx/norm, dy/norm) if norm > 0 else (0, 0)
                        # Convert to metres when saving the points
                        left_wall.append((0.01*(x-l*ey), 0.01*(y+l*ex), 0.01*z))
                        right_wall.append((0.01*(x+r*ey), 0.01*(y-r*ex), 0.01*z))
                        up_down.append((0.01*u, 0.01*d))

                    # Mean elevation of centerline, used for elevation attribute

                    elev = 0.01 * sum([xyzlrud[2] for xyzlrud in centerline]) / len(centerline)
                    attrs = [round(elev, 2)]

                    # Now create the feature sets - first the centerline traverse

                    points = []

                    for xyzlrud in centerline:
                        xyz = [0.01*v for v in xyzlrud[0:3]] # These were mm, convert to metres
                        points.append(QgsPoint(*xyz))

                    linestring = QgsLineString()
                    linestring.setPoints(points)
                    feat = QgsFeature()
                    geom = QgsGeometry(linestring)
                    feat.setGeometry(geom)
                    feat.setAttributes(attrs)
                    trav_features.append(feat)

                    # The walls as line strings

                    for wall in (left_wall, right_wall):

                        points = [QgsPoint(*xyz) for xyz in wall]
                        linestring = QgsLineString()
                        linestring.setPoints(points)
                        feat = QgsFeature()
                        geom = QgsGeometry(linestring)
                        feat.setGeometry(geom)
                        feat.setAttributes(attrs)
                        wall_features.append(feat)

                    # Slightly more elaborate, pair up points on left
                    # and right walls, and build a cross section as a
                    # 2-point line string, and a quadrilateral polygon
                    # with a closed 5-point line string for the
                    # exterior ring.  Note that QGIS polygons are
                    # supposed to have their points ordered clockwise.

                    for i, xyz_pair in enumerate(zip(left_wall, right_wall)):

                        elev = 0.01 * centerline[i][2] # elevation of station in centerline
                        attrs = [round(elev, 2)]
                        points = [QgsPoint(*xyz) for xyz in xyz_pair]
                        linestring = QgsLineString()
                        linestring.setPoints(points)
                        feat = QgsFeature()
                        geom = QgsGeometry(linestring)
                        feat.setGeometry(geom)
                        feat.setAttributes(attrs)
                        xsect_features.append(feat)

                        if i > 0:
                            elev = 0.5*(prev_xyz_pair[0][2] + xyz_pair[0][2]) # average elevation
                            attrs = [round(elev, 2)]
                            if include_up_down: # average up / down
                                attrs += [ 0.5*(v1+v2) for (v1, v2) in zip(up_down[i-1], up_down[i]) ]
                            points = [] # will contain the exterior 5-point ring, as follows...
                            for xyz in tuple(reversed(prev_xyz_pair)) + xyz_pair + (prev_xyz_pair[1],):
                                points.append(QgsPoint(*xyz))
                            linestring = QgsLineString()
                            linestring.setPoints(points)
                            polygon = QgsPolygon()
                            polygon.setExteriorRing(linestring)
                            feat = QgsFeature()
                            geom = QgsGeometry(polygon)
                            feat.setGeometry(geom)
                            feat.setAttributes(attrs)
                            quad_features.append(feat)

                        prev_xyz_pair = xyz_pair

                # End of processing xsect_list - now add features to requested layers

                attrs = [QgsField('ELEVATION', QVariant.Double)] # common to all

                if include_traverses and trav_features: # traverse layer
                    travs_layer = self.add_layer('traverses', 'LineStringZ')
                    travs_layer.dataProvider().addAttributes(attrs)
                    travs_layer.updateFields()
                    travs_layer.dataProvider().addFeatures(trav_features)
                    layers.append(travs_layer)

                if include_xsections and xsect_features: # xsection layer
                    xsects_layer = self.add_layer('xsections', 'LineStringZ')
                    xsects_layer.dataProvider().addAttributes(attrs)
                    xsects_layer.updateFields()
                    xsects_layer.dataProvider().addFeatures(xsect_features)
                    layers.append(xsects_layer)

                if include_walls and wall_features: # wall layer
                    walls_layer = self.add_layer('walls', 'LineStringZ')
                    walls_layer.dataProvider().addAttributes(attrs)
                    walls_layer.updateFields()
                    walls_layer.dataProvider().addFeatures(wall_features)
                    layers.append(walls_layer)

                if include_up_down: # add fields if requested for polygons
                    attrs += [QgsField(s, QVariant.Double) for s in ('MEAN_UP', 'MEAN_DOWN')]

                if include_polygons and quad_features: # polygon layer
                    quads_layer = self.add_layer('polygons', 'PolygonZ')
                    quads_layer.dataProvider().addAttributes(attrs)
                    quads_layer.updateFields()
                    quads_layer.dataProvider().addFeatures(quad_features)
                    layers.append(quads_layer)

            # All layers have been created, now update extents and add to QGIS registry

            if layers:
                [ layer.updateExtents() for layer in layers ]
                QgsProject.instance().addMapLayers(layers)

            # Write to GeoPackage if requested

            if gpkg_file:
                opts = [QgsVectorFileWriter.CreateOrOverwriteFile, QgsVectorFileWriter.CreateOrOverwriteLayer]
                for i, layer in enumerate(layers):
                    options = QgsVectorFileWriter.SaveVectorOptions()
                    options.actionOnExistingFile = opts[int(i > 0)] # create file or layer
                    layer_name = layer.name()
                    match = search(' - ([a-z]*)', layer_name) # ie, extract 'legs', 'stations', etc
                    options.layerName = str(match.group(1)) if match else layer_name
                    writer = QgsVectorFileWriter.writeAsVectorFormat(layer, gpkg_file, options)
                    if writer:
                        msg = "'{}' -> {} in {}".format(layer_name, options.layerName, gpkg_file)
                        QgsMessageLog.logMessage(msg, tag='Import .3d', level=Qgis.Info)
                    options, writer = None, None

        # End of 'if result:' (what happens if user pressed OK)

    # End of run function definition

# That's it
