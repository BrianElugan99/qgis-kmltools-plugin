# -*- coding: utf-8 -*-
"""
/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import os
import re
from PyQt4 import uic
from PyQt4.QtCore import QSettings, QVariant
from PyQt4.QtGui import QDialog

from qgis.core import QgsVectorLayer, QgsPoint, QgsFeature, QgsGeometry, QgsFields, QgsField, QgsMapLayerRegistry
from qgis.gui import QgsMessageBar
from zipfile import ZipFile
import xml.sax, xml.sax.handler
import sys


FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'simplekmldialog.ui'))

        
class SimpleKMLDialog(QDialog, FORM_CLASS):
    def __init__(self, iface):
        """Initialize the QGIS Simple KML inport dialog window."""
        super(SimpleKMLDialog, self).__init__(iface.mainWindow())
        self.setupUi(self)
        self.iface = iface
        self.canvas = iface.mapCanvas()
        
    def accept(self):
        """Called when the OK button has been pressed."""
        pts_name = self.pointsLineEdit.text().strip()
        line_name = self.linesLineEdit.text().strip()
        poly_name = self.polyLineEdit.text().strip()
        fp = self.fileWidget.filePath()
        filename, extension = os.path.splitext(fp)
        extension = extension.lower()
        try:
            if extension == '.kmz':
                kmz = ZipFile(fp, 'r')
                kml = kmz.open('doc.kml', 'r')
            elif extension == '.kml':
                kml = open(fp, 'r')
            else:
                self.iface.messageBar().pushMessage("", "Invalid extension: Should be kml or kmz", level=QgsMessageBar.WARNING, duration=4)
                return
        except:
            self.iface.messageBar().pushMessage("", "Failed to open file", level=QgsMessageBar.WARNING, duration=4)
            return
        
        parser = xml.sax.make_parser()
        handler = PlacemarkHandler(self.iface, pts_name, line_name, poly_name)
        parser.setContentHandler(handler)
        parser.parse(kml)
        
        if extension == 'kmz':
            kmz.close()
        else:
            kml.close()
        self.close()

class PlacemarkHandler(xml.sax.handler.ContentHandler):
    def __init__(self, iface, pts_name, line_name, poly_name):
        self.iface = iface
        self.pts_name = pts_name
        self.line_name = line_name
        self.poly_name = poly_name
        self.hasPts = False
        self.hasLine = False
        self.hasPoly = False
        
        self.inFolder = False
        self.inName = False 
        self.inPlacemark = False
        self.inDescription = False
        self.inCoordinates = False
        self.inLatitude = False
        self.inLongitude = False
        self.inAltitude = False
        self.inLocation = False
        self.type = 0 # 0 point, 1 location, 2 linestring, 3 Polygon
        self.name = ""
        self.folders = []
        self.description = ""
        self.coord = ""
        self.lon = ""
        self.lat = ""
        self.altitude = ""
        
    def startElement(self, name, attributes):
        if name == "Folder":
            self.inFolder = True
            self.name = ""
            
        if self.inFolder and not self.inPlacemark:
            if name == "name":
                self.inName = True 
                self.name = ""
            
        if name == "Placemark":
            self.inPlacemark = True
            self.inFolder = False
            self.name = ""
            self.folder = ""
            self.description = ""
            self.coord = ""
            self.lon = ""
            self.lat = ""
            self.altitude = ""

        if self.inPlacemark:
            if name == "Point":
                self.type = 0
            elif name == "Location":
                self.inLocation = True
                self.type = 1
            elif name == "LineString":
                self.type = 2
            elif name == "Polygon":
                self.type = 3
            elif name == "name": 
                self.inName = True 
                self.name = ""
            elif name == "description": 
                self.inDescription = True
                self.description = ""
            elif name == "coordinates":
                self.inCoordinates = True
                self.coord = ""
            elif name == "longitude" and self.inLocation:
                self.inLongitude = True
                self.lon = ""
            elif name == "latitude" and self.inLocation:
                self.inLatitude = True
                self.lat = ""
            elif name == "altitude" and self.inLocation:
                self.inAltitude = True
                self.altitude = ""
            
    def characters(self, data):
        #print( "data: '" + data+"'")
        if self.inName: # on text within tag
            self.name += data # save text if in title
        elif self.inDescription:
            self.description += data
        elif self.inCoordinates:
            self.coord += data
        elif self.inLongitude and self.inLocation:
            self.lon += data
        elif self.inLatitude and self.inLocation:
            self.lat += data
        elif self.inAltitude and self.inLocation:
            self.altitude += data
            

    def endElement(self, name):
        if self.inPlacemark:
            if name == "name":
                self.inName = False # on end title tag
                self.name = self.name.strip()
            elif name == "description":
                self.inDescription = False
                self.description = self.description.strip()
            elif name == "coordinates":
                self.inCoordinates = False
                self.coord = self.coord.strip()
            elif name == "longitude" and self.inLocation:
                self.inLongitude = False
                self.lon = self.lon.strip()
            elif name == "latitude" and self.inLocation:
                self.inLatitude = False
                self.lat = self.lat.strip()
            elif name == "altitude" and self.inLocation:
                self.inAltitude = False
                self.altitude = self.altitude.strip()
            elif name == "Location":
                self.inLocation = False
                self.inLongitude = False
                self.inLatitude = False
                self.inAltitude = False
            elif name == "Placemark":
                self.inPlacemark = False
                self.inName = False
                self.inDescription = False
                self.inCoordinates = False
                self.inLongitude = False
                self.inLatitude = False
                self.inAltitude = False
                self.process(self.type, self.name, self.description, self.coord, self.lon, self.lat, self.altitude)
        elif name == 'Folder':
            self.inFolder = False
            if len(self.folders) > 0:
                del self.folders[-1]
        elif self.inFolder:
            if name == 'name':
                self.inName = False # on end title tag
                self.inFolder = False
                self.name = self.name.strip()
                self.folders.append(self.name)
        else:
            self.inName = False
            self.inDescription = False
            self.inCoordinates = False
            self.inLongitude = False
            self.inLatitude = False
            self.inAltitude = False
            
    def endDocument(self):
        if self.hasPts: # We found kml points so we need to end the layer
            self.ptLayer.updateExtents()
            QgsMapLayerRegistry.instance().addMapLayer(self.ptLayer)
        if self.hasLine:
            self.lineLayer.updateExtents()
            QgsMapLayerRegistry.instance().addMapLayer(self.lineLayer)
            
    def folderString(self):
        if len(self.folders) > 0:
            return(u"; ".join(self.folders))
        else:
            return("")
    
    def process(self, type, name, desc, coord, lon, lat, altitude):
        if type <= 1:
            if not self.hasPts:
                self.ptLayer = QgsVectorLayer("Point?crs=epsg:4326", self.pts_name, "memory")
                f = QgsFields()
                f.append(QgsField("name", QVariant.String))
                f.append(QgsField("folders", QVariant.String))
                f.append(QgsField("description", QVariant.String))
                f.append(QgsField("altitude", QVariant.Double))
                self.ptLayer.dataProvider().addAttributes(f)
                self.ptLayer.updateFields()
                self.hasPts = True
            if type == 0:
                c = coord.split(',')
                lat = 0.0
                lon = 0.0
                altitude = 0.0
                try:
                    lon = float( c[0] )
                    lat = float( c[1] )
                    if len(c) >= 3:
                        altitude = float(c[2])
                except:
                    pass
            else:
                lon = float(lon)
                lat = float(lat)
                altitude = float(altitude)
                
            feature = QgsFeature()
            feature.setGeometry(QgsGeometry.fromPoint(QgsPoint(lon,lat)))
            attr = [name, self.folderString(), desc, altitude]
            feature.setAttributes(attr)
            self.ptLayer.dataProvider().addFeatures([feature])
            
        elif type == 2: #LineString
            if not self.hasLine:
                self.lineLayer = QgsVectorLayer("LineString?crs=epsg:4326", self.line_name, "memory")
                f = QgsFields()
                f.append(QgsField("name", QVariant.String))
                f.append(QgsField("folders", QVariant.String))
                f.append(QgsField("description", QVariant.String))
                self.lineLayer.dataProvider().addAttributes(f)
                self.lineLayer.updateFields()
                self.hasLine = True
                
            pts = coord2pts(coord)
            
            feature = QgsFeature()
            feature.setGeometry(QgsGeometry.fromPolyline(pts))
            attr = [name, self.folderString(), desc]
            feature.setAttributes(attr)
            self.lineLayer.dataProvider().addFeatures([feature])
            
            
            
def coord2pts(coords):
    pts = []
    coords = coords.strip()
    clist = re.split('\s+', coords)
    print "number of line coords: ", len(clist)
    
    for pt in clist:
        c = pt.split(',')
        try:
            lon = float(c[0])
            lat = float(c[1])
        except:
            lon = 0.0
            lat = 0.0
        pts.append(QgsPoint(lon,lat))
        
    return(pts)
    