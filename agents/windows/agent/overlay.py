"""Blocking screen overlay.

Displays a semi-transparent fullscreen overlay when an application is
blocked because its daily time-limit has been reached.  Built on
:mod:`tkinter` (stdlib) so that no additional GUI dependencies are
required.
"""

from __future__ import annotations

import logging
import threading
import webbrowser
from typing import Callable

from .config import AgentConfig

log = logging.getLogger(__name__)

# tkinter is part of the stdlib but may not be installed on every system.
try:
    import tkinter as tk
    from tkinter import simpledialog

    _HAS_TK = True
except ImportError:  # pragma: no cover
    _HAS_TK = False
    log.warning("tkinter is not available -- overlay will be disabled.")

# -- constants ---------------------------------------------------------------

_OVERLAY_BG = "#1a1a2e"
_ACCENT = "#e94560"
_TEXT_FG = "#eaeaea"
_BTN_BG = "#16213e"
_BTN_FG = "#e94560"
_AUTO_DISMISS_MS = 30_000  # 30 seconds

_SHIELD_ART = r"""
     ___________
    /     |     \
   /      |      \
  |   ----+----   |
  |       |       |
   \      |      /
    \     |     /
     \____|____/
"""


class BlockingOverlay:
    """Tkinter-based fullscreen overlay shown when an app is blocked.

    Parameters
    ----------
    config:
        The shared agent configuration.  ``config.server_url`` is used
        to construct URLs for the PWA.
    """

    def __init__(self, config: AgentConfig) -> None:
        self._config = config
        self._root: tk.Tk | None = None
        self._thread: threading.Thread | None = None
        self.on_tan_entered: Callable[[str], None] | None = None
        self.on_totp_entered: Callable[[str], None] | None = None

    # -- public API -----------------------------------------------------------

    def show(
        self,
        app_name: str,
        group_name: str,
        used_minutes: int,
        limit_minutes: int,
    ) -> None:
        """Display the blocking overlay.

        The overlay runs in a dedicated daemon thread so that the caller
        (typically the async monitor loop) is not blocked.
        """
        if not _HAS_TK:
            log.warning("Cannot show overlay -- tkinter unavailable.")
            return

        # Dismiss any existing overlay before showing a new one.
        self.dismiss()

        self._thread = threading.Thread(
            target=self._run,
            args=(app_name, group_name, used_minutes, limit_minutes),
            daemon=True,
            name="heimdall-overlay",
        )
        self._thread.start()
        log.info("Overlay shown for '%s' (%s).", app_name, group_name)

    def dismiss(self) -> None:
        """Programmatically close the overlay if it is open."""
        root = self._root
        if root is not None:
            try:
                root.after(0, root.destroy)
            except Exception:
                pass
            self._root = None
        log.debug("Overlay dismissed.")

    # -- internal -------------------------------------------------------------

    def _run(
        self,
        app_name: str,
        group_name: str,
        used_minutes: int,
        limit_minutes: int,
    ) -> None:
        """Build and show the overlay window (called in a thread)."""
        root = tk.Tk()
        self._root = root

        root.title("Heimdall")
        root.configure(bg=_OVERLAY_BG)
        root.attributes("-topmost", True)

        # Attempt fullscreen; fall back to a large centered window.
        try:
            root.attributes("-fullscreen", True)
        except tk.TclError:
            root.geometry("800x600")
            _centre_window(root, 800, 600)

        # Try to set a semi-transparent background (platform-dependent).
        try:
            root.attributes("-alpha", 0.92)
        except tk.TclError:
            pass

        root.overrideredirect(True)

        # -- content ----------------------------------------------------------

        frame = tk.Frame(root, bg=_OVERLAY_BG)
        frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        # Shield icon (text art)
        tk.Label(
            frame,
            text=_SHIELD_ART,
            font=("Courier", 14),
            fg=_ACCENT,
            bg=_OVERLAY_BG,
            justify=tk.CENTER,
        ).pack(pady=(0, 10))

        # Title
        tk.Label(
            frame,
            text=f"{app_name} ist gerade pausiert",
            font=("Segoe UI", 28, "bold"),
            fg=_TEXT_FG,
            bg=_OVERLAY_BG,
        ).pack(pady=(0, 8))

        # Group label
        tk.Label(
            frame,
            text=group_name,
            font=("Segoe UI", 16),
            fg=_ACCENT,
            bg=_OVERLAY_BG,
        ).pack(pady=(0, 20))

        # Time info
        tk.Label(
            frame,
            text=(
                f"Gaming-Zeit f\u00fcr heute: "
                f"{used_minutes} / {limit_minutes} Minuten aufgebraucht"
            ),
            font=("Segoe UI", 14),
            fg=_TEXT_FG,
            bg=_OVERLAY_BG,
        ).pack(pady=(0, 30))

        # -- buttons ----------------------------------------------------------

        btn_frame = tk.Frame(frame, bg=_OVERLAY_BG)
        btn_frame.pack(pady=(0, 20))

        tk.Button(
            btn_frame,
            text="TAN eingeben",
            font=("Segoe UI", 13),
            fg=_BTN_FG,
            bg=_BTN_BG,
            activebackground=_ACCENT,
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=20,
            pady=10,
            command=lambda: self._show_tan_dialog(root),
        ).pack(side=tk.LEFT, padx=10)

        tk.Button(
            btn_frame,
            text="Eltern-Code",
            font=("Segoe UI", 13),
            fg=_BTN_FG,
            bg=_BTN_BG,
            activebackground=_ACCENT,
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=20,
            pady=10,
            command=lambda: self._show_totp_dialog(root),
        ).pack(side=tk.LEFT, padx=10)

        tk.Button(
            btn_frame,
            text="Quests anzeigen",
            font=("Segoe UI", 13),
            fg=_BTN_FG,
            bg=_BTN_BG,
            activebackground=_ACCENT,
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=20,
            pady=10,
            command=lambda: self._open_pwa("/quests"),
        ).pack(side=tk.LEFT, padx=10)

        # Close / dismiss button
        tk.Button(
            frame,
            text="\u00d7",  # multiplication sign as close icon
            font=("Segoe UI", 18),
            fg=_TEXT_FG,
            bg=_OVERLAY_BG,
            activebackground=_ACCENT,
            activeforeground="#ffffff",
            bd=0,
            command=root.destroy,
        ).place(relx=1.0, rely=0.0, anchor=tk.NE)

        # Auto-dismiss after timeout.
        root.after(_AUTO_DISMISS_MS, root.destroy)

        try:
            root.mainloop()
        except Exception:
            log.debug("Overlay mainloop exited.")
        finally:
            self._root = None

    # -- helpers --------------------------------------------------------------

    def _open_pwa(self, path: str) -> None:
        """Open the default web browser pointing at the Heimdall PWA."""
        url = f"{self._config.server_url}{path}"
        log.info("Opening PWA URL: %s", url)
        try:
            webbrowser.open(url)
        except Exception:
            log.exception("Failed to open browser for %s", url)

    def _show_totp_dialog(self, parent: tk.Tk | None = None) -> None:
        """Show a numeric input dialog for TOTP (6-digit parent code) entry."""
        if not _HAS_TK:
            return

        code = simpledialog.askstring(
            "Eltern-Code eingeben",
            "Bitte gib den 6-stelligen Eltern-Code ein:",
            parent=parent,
        )

        if code and code.strip():
            code = code.strip()
            log.info("TOTP code entered (length=%d).", len(code))
            if self.on_totp_entered is not None:
                try:
                    self.on_totp_entered(code)
                except Exception:
                    log.exception("on_totp_entered callback failed")
        else:
            log.debug("TOTP dialog cancelled or empty input.")

    def _show_tan_dialog(self, parent: tk.Tk | None = None) -> None:
        """Show a simple input dialog for TAN entry.

        When the user enters a TAN and clicks OK the
        :attr:`on_tan_entered` callback is invoked.
        """
        if not _HAS_TK:
            return

        tan = simpledialog.askstring(
            "TAN eingeben",
            "Bitte gib den TAN-Code ein:",
            parent=parent,
        )

        if tan and tan.strip():
            tan = tan.strip()
            log.info("TAN entered (length=%d).", len(tan))
            if self.on_tan_entered is not None:
                try:
                    self.on_tan_entered(tan)
                except Exception:
                    log.exception("on_tan_entered callback failed")
        else:
            log.debug("TAN dialog cancelled or empty input.")


# -- utility ------------------------------------------------------------------


def _centre_window(window: tk.Tk, width: int, height: int) -> None:
    """Move *window* to the centre of the screen."""
    screen_w = window.winfo_screenwidth()
    screen_h = window.winfo_screenheight()
    x = (screen_w - width) // 2
    y = (screen_h - height) // 2
    window.geometry(f"{width}x{height}+{x}+{y}")
