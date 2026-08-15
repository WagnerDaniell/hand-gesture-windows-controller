"""
Global Hotkey and Emergency Killswitch Listener.
Monitors global keyboard events asynchronously in the background.
"""

import threading
from typing import Callable, Optional
from pynput import keyboard


class GlobalHotkeyListener:
    """
    Asynchronous keyboard listener for emergency stop and gesture pause/resume toggles.
    """

    def __init__(
        self,
        on_emergency_stop: Optional[Callable[[], None]] = None,
        on_toggle_pause: Optional[Callable[[], None]] = None,
        on_toggle_hud: Optional[Callable[[], None]] = None,
        on_cycle_monitors: Optional[Callable[[], None]] = None,
        emergency_key: str = "esc",
        pause_key: str = "f8",
    ):
        self.on_emergency_stop = on_emergency_stop
        self.on_toggle_pause = on_toggle_pause
        self.on_toggle_hud = on_toggle_hud
        self.on_cycle_monitors = on_cycle_monitors
        
        self.emergency_key = emergency_key.lower()
        self.pause_key = pause_key.lower()

        self._listener: Optional[keyboard.Listener] = None
        self._is_running = False

    def start(self):
        """Start global keyboard hook thread."""
        if self._is_running:
            return

        self._is_running = True
        self._listener = keyboard.Listener(on_press=self._handle_key_press)
        self._listener.daemon = True
        self._listener.start()

    def _handle_key_press(self, key):
        """Internal callback when any key is pressed anywhere in Windows."""
        try:
            key_name = ""
            if hasattr(key, "name") and key.name:
                key_name = key.name.lower()
            elif hasattr(key, "char") and key.char:
                key_name = key.char.lower()

            if key_name == self.emergency_key:
                if self.on_emergency_stop:
                    self.on_emergency_stop()

            elif key_name == self.pause_key:
                if self.on_toggle_pause:
                    self.on_toggle_pause()

        except Exception:
            pass

    def stop(self):
        """Stop keyboard listener."""
        if self._listener:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None
        self._is_running = False
