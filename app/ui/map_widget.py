"""
Interactive Map Widget hosting Leaflet.js inside QWebEngineView
with bidirectional QWebChannel communication.
"""

import os
import json
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QUrl
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings
from PyQt6.QtWebChannel import QWebChannel


class MapBridge(QObject):
    """Bridge object exposed to JavaScript inside QWebEngineView."""
    sig_coordinates_selected = pyqtSignal(float, float)

    @pyqtSlot(float, float)
    def onMapClicked(self, lat: float, lng: float):
        """Called from Leaflet map click event."""
        self.sig_coordinates_selected.emit(lat, lng)


class MapWidget(QWidget):
    """Widget embedding the interactive Leaflet map."""
    sig_location_changed = pyqtSignal(float, float)

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.web_view = QWebEngineView(self)
        layout.addWidget(self.web_view)

        # Enable local content & remote tile access
        settings = self.web_view.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.ScrollAnimatorEnabled, True)

        # Setup WebChannel
        self.bridge = MapBridge(self)
        self.bridge.sig_coordinates_selected.connect(self._on_bridge_coords)

        self.channel = QWebChannel(self.web_view.page())
        self.channel.registerObject("pyBridge", self.bridge)
        self.web_view.page().setWebChannel(self.channel)

        self._page_loaded = False
        self._pending_coords = None
        self.web_view.loadFinished.connect(self._on_load_finished)

        # Load map HTML
        html_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "assets", "map.html")
        )
        self.web_view.load(QUrl.fromLocalFile(html_path))

    def _on_load_finished(self, ok: bool):
        self._page_loaded = True
        if self._pending_coords:
            lat, lon, zoom = self._pending_coords
            script = f"if (window.flyToLocation) {{ window.flyToLocation({lat}, {lon}, {zoom}); }}"
            self.web_view.page().runJavaScript(script)

    def _on_bridge_coords(self, lat: float, lng: float):
        self.sig_location_changed.emit(lat, lng)

    def set_coordinates(self, lat: float, lon: float, pan: bool = True):
        """Updates the map marker to the specified coordinates from Python."""
        pan_str = "true" if pan else "false"
        script = f"if (window.setMarkerLocation) {{ window.setMarkerLocation({lat}, {lon}, {pan_str}); }}"
        self.web_view.page().runJavaScript(script)

    def fly_to(self, lat: float, lon: float, zoom: int = 14):
        """Smoothly pans and zooms to the location."""
        self._pending_coords = (lat, lon, zoom)
        if self._page_loaded:
            script = f"if (window.flyToLocation) {{ window.flyToLocation({lat}, {lon}, {zoom}); }}"
            self.web_view.page().runJavaScript(script)

    def draw_route(self, coords: list):
        """Draws route polyline on the Leaflet map."""
        coords_json = json.dumps([[pt[0], pt[1]] for pt in coords])
        script = f"if (window.drawRoute) {{ window.drawRoute({coords_json}); }}"
        self.web_view.page().runJavaScript(script)

    def clear_route(self):
        """Removes the route polyline from the map."""
        script = "if (window.clearRoute) { window.clearRoute(); }"
        self.web_view.page().runJavaScript(script)
