"""System-tray icon for the Heimdall Windows agent.

Uses *pystray* for the native tray icon and *Pillow* to render colored
shield/circle icons on the fly so no external image assets are required.

Icon states
-----------
- ``connected`` -- green  (agent connected, everything OK)
- ``warning``   -- yellow (less than 5 min remaining for a group)
- ``blocked``   -- red    (an app group is currently locked)
- ``offline``   -- gray   (no connection to the Heimdall server)
"""

from __future__ import annotations

import logging
import webbrowser
from typing import Callable

from .config import AgentConfig

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Graceful handling of missing native dependencies
# ---------------------------------------------------------------------------
try:
    import pystray  # type: ignore[import-untyped]
    from PIL import Image, ImageDraw, ImageFont  # type: ignore[import-untyped]

    _HAS_TRAY_DEPS = True
except ImportError:
    _HAS_TRAY_DEPS = False
    pystray = None  # type: ignore[assignment]
    Image = None  # type: ignore[assignment,misc]
    ImageDraw = None  # type: ignore[assignment]
    ImageFont = None  # type: ignore[assignment]
    log.warning(
        "pystray and/or Pillow not installed -- tray icon will be unavailable. "
        "Install them with: pip install pystray Pillow"
    )

# ---------------------------------------------------------------------------
# Color palette for each status
# ---------------------------------------------------------------------------
_STATUS_COLORS: dict[str, str] = {
    "connected": "#22c55e",  # green-500
    "warning": "#eab308",    # yellow-500
    "blocked": "#ef4444",    # red-500
    "offline": "#9ca3af",    # gray-400
}

_ICON_SIZE = 64


class TrayIcon:
    """Manages the Heimdall system-tray icon, menu, and status updates.

    Parameters
    ----------
    config:
        The current ``AgentConfig`` instance used to derive the PWA URL and
        other display information.
    """

    def __init__(self, config: AgentConfig) -> None:
        self._config = config
        self._icon: pystray.Icon | None = None  # type: ignore[union-attr]
        self._status: str = "offline"  # connected | warning | blocked | offline
        self._group_times: dict[str, tuple[int, int]] = {}  # group -> (used, limit)

        # Public callbacks -- set by the orchestrating code before calling run()
        self.on_tan_entry: Callable[[], None] | None = None
        self.on_quit: Callable[[], None] | None = None

    # ------------------------------------------------------------------
    # Icon rendering
    # ------------------------------------------------------------------

    @staticmethod
    def _create_icon_image(color: str) -> Image.Image:  # type: ignore[name-defined]
        """Generate a 64x64 RGBA image with a coloured circle and a white 'H'.

        Parameters
        ----------
        color:
            Any colour string accepted by Pillow (hex, named, ...).

        Returns
        -------
        PIL.Image.Image
            The rendered icon image.
        """
        img = Image.new("RGBA", (_ICON_SIZE, _ICON_SIZE), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Draw the filled circle (shield placeholder)
        padding = 2
        draw.ellipse(
            [padding, padding, _ICON_SIZE - padding, _ICON_SIZE - padding],
            fill=color,
            outline=color,
        )

        # Draw a centered white 'H'
        letter = "H"
        try:
            # Attempt to use a TrueType font for a nicer look
            font = ImageFont.truetype("arial.ttf", 36)
        except (OSError, IOError):
            # Fall back to the built-in bitmap font
            try:
                font = ImageFont.load_default(size=36)
            except TypeError:
                # Older Pillow versions do not accept a size argument
                font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), letter, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        text_x = (_ICON_SIZE - text_w) / 2 - bbox[0]
        text_y = (_ICON_SIZE - text_h) / 2 - bbox[1]
        draw.text((text_x, text_y), letter, fill="white", font=font)

        return img

    # ------------------------------------------------------------------
    # Menu construction
    # ------------------------------------------------------------------

    def _build_menu(self) -> pystray.Menu:  # type: ignore[name-defined]
        """Build the right-click context menu for the tray icon."""
        items: list[pystray.MenuItem] = []  # type: ignore[name-defined]

        # -- Header --------------------------------------------------------
        items.append(
            pystray.MenuItem("HEIMDALL Status", None, enabled=False),
        )
        items.append(pystray.Menu.SEPARATOR)

        # -- Per-group time counters --------------------------------------
        if self._group_times:
            for group_name, (used, limit) in sorted(self._group_times.items()):
                label = f"{group_name}: {used} / {limit} Min"
                items.append(pystray.MenuItem(label, None, enabled=False))
            items.append(pystray.Menu.SEPARATOR)

        # -- Actions -------------------------------------------------------
        items.append(
            pystray.MenuItem("TAN eingeben", self._on_tan_clicked),
        )
        items.append(
            pystray.MenuItem("Quests anzeigen", self._on_quests_clicked),
        )
        items.append(pystray.Menu.SEPARATOR)

        # -- Connection status ---------------------------------------------
        status_label = (
            "Agent: Connected" if self._status == "connected" else "Agent: Offline"
        )
        items.append(pystray.MenuItem(status_label, None, enabled=False))
        items.append(pystray.Menu.SEPARATOR)

        # -- Exit ----------------------------------------------------------
        items.append(
            pystray.MenuItem("Beenden", self._on_quit_clicked),
        )

        return pystray.Menu(*items)

    # ------------------------------------------------------------------
    # Menu callbacks
    # ------------------------------------------------------------------

    def _on_tan_clicked(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:  # type: ignore[name-defined]
        """Handle *TAN eingeben* menu click."""
        log.debug("TAN entry requested via tray menu.")
        if self.on_tan_entry is not None:
            try:
                self.on_tan_entry()
            except Exception:
                log.exception("Error in on_tan_entry callback")
        else:
            log.warning("on_tan_entry callback not set -- ignoring click.")

    def _on_quests_clicked(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:  # type: ignore[name-defined]
        """Open the Heimdall PWA in the default browser."""
        pwa_url = f"{self._config.server_url}/quests"
        log.info("Opening quests PWA: %s", pwa_url)
        try:
            webbrowser.open(pwa_url)
        except Exception:
            log.exception("Failed to open browser for quests URL: %s", pwa_url)

    def _on_quit_clicked(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:  # type: ignore[name-defined]
        """Handle *Beenden* menu click."""
        log.info("Quit requested via tray menu.")
        if self.on_quit is not None:
            try:
                self.on_quit()
            except Exception:
                log.exception("Error in on_quit callback")
        # Always stop the icon loop so the thread can exit cleanly.
        self.stop()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update_status(self, status: str) -> None:
        """Update the tray-icon colour to reflect the new *status*.

        Parameters
        ----------
        status:
            One of ``connected``, ``warning``, ``blocked``, ``offline``.
        """
        if status not in _STATUS_COLORS:
            log.warning("Unknown tray status %r -- falling back to 'offline'.", status)
            status = "offline"

        self._status = status
        log.debug("Tray status changed to %s.", status)

        if self._icon is not None:
            try:
                self._icon.icon = self._create_icon_image(_STATUS_COLORS[status])
                # Rebuild the menu so the status line reflects the change
                self._icon.menu = self._build_menu()
                self._icon.update_menu()
            except Exception:
                log.exception("Failed to update tray icon for status %s.", status)

    def update_group_times(
        self, group_times: dict[str, tuple[int, int]]
    ) -> None:
        """Replace the displayed per-group time counters.

        Parameters
        ----------
        group_times:
            Mapping of *group_name* to ``(used_minutes, limit_minutes)``.
        """
        self._group_times = dict(group_times)
        log.debug("Group times updated: %s", self._group_times)

        if self._icon is not None:
            try:
                self._icon.menu = self._build_menu()
                self._icon.update_menu()
            except Exception:
                log.exception("Failed to refresh tray menu after group-time update.")

    def run(self) -> None:
        """Create and start the tray icon.

        .. warning::
            This method **blocks** the calling thread.  It is intended to be
            called from a dedicated ``threading.Thread``.
        """
        if not _HAS_TRAY_DEPS:
            log.error(
                "Cannot start tray icon -- pystray/Pillow not available."
            )
            return

        image = self._create_icon_image(_STATUS_COLORS[self._status])
        menu = self._build_menu()

        self._icon = pystray.Icon(
            name="heimdall-agent",
            icon=image,
            title="Heimdall Agent",
            menu=menu,
        )

        log.info("Starting Heimdall tray icon (status=%s).", self._status)
        try:
            self._icon.run()
        except Exception:
            log.exception("Tray icon exited with error.")
        finally:
            self._icon = None
            log.info("Tray icon stopped.")

    def stop(self) -> None:
        """Stop the tray icon if it is currently running."""
        if self._icon is not None:
            log.info("Stopping Heimdall tray icon.")
            try:
                self._icon.stop()
            except Exception:
                log.exception("Error while stopping tray icon.")
