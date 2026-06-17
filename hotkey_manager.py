import threading
from pynput import keyboard


class HotkeyManager:
    def __init__(self):
        self._listener = None
        self._registered = {}
        self._lock = threading.Lock()

    def start(self):
        if self._listener is not None:
            return
        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self._listener.daemon = True
        self._listener.start()

    def stop(self):
        if self._listener is not None:
            self._listener.stop()
            self._listener = None
        with self._lock:
            self._registered.clear()

    def register(self, hotkey_str, callback):
        if not hotkey_str:
            return
        with self._lock:
            self._registered[hotkey_str] = callback
        self._restart_listener()

    def unregister(self, hotkey_str):
        with self._lock:
            self._registered.pop(hotkey_str, None)
        self._restart_listener()

    def clear_all(self):
        with self._lock:
            self._registered.clear()
        self._restart_listener()

    def register_multiple(self, hotkey_map):
        with self._lock:
            self._registered.update(hotkey_map)
        self._restart_listener()

    def _restart_listener(self):
        was_running = self._listener is not None
        if was_running:
            self._listener.stop()
            self._listener = None

        with self._lock:
            if not self._registered:
                return
            hotkeys = keyboard.HotKey.parse(list(self._registered.keys()))
            callbacks = list(self._registered.values())

        if not hotkeys:
            return

        def _canonical(f):
            def wrapper(key):
                f(canonical(key))
            return wrapper

        canonical = self._listener_canonical if was_running else None
        self._listener = keyboard.Listener(
            on_press=self._make_on_press(hotkeys, callbacks),
        )
        self._listener.daemon = True
        self._listener.start()

    def _make_on_press(self, hotkeys, callbacks):
        pressed = set()

        def on_press(key):
            try:
                canonical_key = self._canonicalize(key)
                pressed.add(canonical_key)
            except Exception:
                return

            for hotkey, callback in zip(hotkeys, callbacks):
                hotkey_set = set(hotkey) if not isinstance(hotkey, set) else hotkey
                if hotkey_set.issubset(pressed):
                    try:
                        callback()
                    except Exception:
                        pass

        def on_release(key):
            try:
                canonical_key = self._canonicalize(key)
                pressed.discard(canonical_key)
            except Exception:
                pass

        return on_press, on_release

    def _canonicalize(self, key):
        if isinstance(key, keyboard.Key):
            return key
        if isinstance(key, keyboard.KeyCode):
            return key
        return key

    def _on_press(self, key):
        pass

    def _on_release(self, key):
        pass

    @property
    def _listener_canonical(self):
        return None


class SimpleHotkeyManager:
    def __init__(self):
        self._listener = None
        self._hotkeys = {}
        self._current_keys = set()

    def start(self):
        if self._listener is not None:
            return
        self._listener = keyboard.GlobalHotKeys({})
        self._listener.daemon = True
        self._listener.start()

    def stop(self):
        if self._listener is not None:
            self._listener.stop()
            self._listener = None
        self._hotkeys.clear()

    def register(self, hotkey_str, callback):
        if not hotkey_str:
            return
        self.unregister(hotkey_str)
        self._hotkeys[hotkey_str] = callback
        self._rebuild()

    def unregister(self, hotkey_str):
        self._hotkeys.pop(hotkey_str, None)
        self._rebuild()

    def register_multiple(self, hotkey_map):
        for hk, cb in hotkey_map.items():
            if hk:
                self._hotkeys[hk] = cb
        self._rebuild()

    def clear_all(self):
        self._hotkeys.clear()
        self._rebuild()

    def _rebuild(self):
        was_running = self._listener is not None
        if was_running:
            self._listener.stop()
            self._listener = None

        if not self._hotkeys:
            return

        self._listener = keyboard.GlobalHotKeys(self._hotkeys)
        self._listener.daemon = True
        self._listener.start()

    @staticmethod
    def format_hotkey(modifiers, key):
        parts = []
        if "ctrl" in modifiers:
            parts.append("<ctrl>")
        if "alt" in modifiers:
            parts.append("<alt>")
        if "shift" in modifiers:
            parts.append("<shift>")
        if "cmd" in modifiers or "win" in modifiers:
            parts.append("<cmd>")
        parts.append(key)
        return "+".join(parts)
