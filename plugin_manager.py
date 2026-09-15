import os
import sys
import json
import logging
import importlib.util
import traceback
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

PLUGINS_DIR = Path(__file__).parent / "plugins"
PLUGINS_DIR.mkdir(parents=True, exist_ok=True)


class BasePlugin:
    """Base class interface for all M.A.R.K.E.T AI Plugins."""
    plugin_id: str = "base_plugin"
    name: str = "إضافة أساسية"
    description: str = "وصف الإضافة"
    version: str = "1.0.0"
    author: str = "Local AI"
    enabled: bool = True

    def on_message_received(self, user_id: str, message: str) -> Optional[Dict[str, Any]]:
        """Hook called when a customer message is received."""
        return None

    def on_reply_generated(self, user_id: str, prompt: str, reply: str, metadata: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Hook called after AI generates a reply."""
        return None

    def on_purchase_detected(self, user_id: str, product_code: str, details: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Hook called when a purchase intent or order is confirmed."""
        return None

    def get_ui_snippet(self) -> Optional[str]:
        """Optional hook to inject HTML/CSS snippet into the frontend dashboard."""
        return None


class PluginManager:
    """
    Manages loading, execution, dynamic toggling, and AI generation of plugins.
    """
    def __init__(self):
        self.plugins: Dict[str, BasePlugin] = {}
        self.plugin_states: Dict[str, bool] = {}
        self.load_plugins()

    def load_plugins(self):
        """Dynamically load all python plugin modules from plugins/ directory."""
        self.plugins.clear()
        
        for file in PLUGINS_DIR.glob("*.py"):
            if file.name.startswith("__"):
                continue

            plugin_id = file.stem
            try:
                spec = importlib.util.spec_from_file_location(plugin_id, file)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[plugin_id] = module
                    spec.loader.exec_module(module)

                    # Look for Plugin class
                    if hasattr(module, "Plugin") and issubclass(module.Plugin, BasePlugin):
                        instance = module.Plugin()
                        instance.plugin_id = plugin_id
                        
                        # Preserve toggle state
                        if plugin_id in self.plugin_states:
                            instance.enabled = self.plugin_states[plugin_id]
                        else:
                            self.plugin_states[plugin_id] = instance.enabled

                        self.plugins[plugin_id] = instance
                        logger.info(f"[PluginManager] Loaded plugin: '{instance.name}' (ID: {plugin_id}, Enabled: {instance.enabled})")
            except Exception as e:
                logger.error(f"[PluginManager] Failed to load plugin '{file.name}': {e}\n{traceback.format_exc()}")

    def set_plugin_state(self, plugin_id: str, enabled: bool):
        """Enable or disable a plugin by ID."""
        self.plugin_states[plugin_id] = enabled
        if plugin_id in self.plugins:
            self.plugins[plugin_id].enabled = enabled
            logger.info(f"[PluginManager] Plugin '{plugin_id}' state updated to: {enabled}")

    def list_plugins(self) -> List[Dict[str, Any]]:
        """Return structured list of all installed plugins."""
        result = []
        for pid, p in self.plugins.items():
            ui_snip = None
            if hasattr(p, "get_ui_snippet"):
                try:
                    ui_snip = p.get_ui_snippet()
                except Exception:
                    pass

            result.append({
                "plugin_id": pid,
                "id": pid,
                "name": p.name,
                "description": p.description,
                "version": p.version,
                "author": p.author,
                "enabled": p.enabled,
                "file_name": f"{pid}.py",
                "filename": f"{pid}.py",
                "ui_snippet": ui_snip
            })
        return result

    def trigger_message_hook(self, user_id: str, message: str) -> List[Dict[str, Any]]:
        """Trigger on_message_received across all active plugins."""
        results = []
        for pid, p in self.plugins.items():
            if p.enabled:
                try:
                    res = p.on_message_received(user_id, message)
                    if res:
                        results.append({"plugin_id": pid, "output": res})
                except Exception as e:
                    logger.error(f"[PluginHook Error] Plugin '{pid}' failed on_message: {e}")
        return results

    def trigger_reply_hook(self, user_id: str, prompt: str, reply: str, metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Trigger on_reply_generated across all active plugins."""
        results = []
        meta = metadata or {}
        for pid, p in self.plugins.items():
            if p.enabled:
                try:
                    res = p.on_reply_generated(user_id, prompt, reply, meta)
                    if res:
                        results.append({"plugin_id": pid, "output": res})
                except Exception as e:
                    logger.error(f"[PluginHook Error] Plugin '{pid}' failed on_reply: {e}")
        return results

    def trigger_purchase_hook(self, user_id: str, product_code: str, details: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Trigger on_purchase_detected across all active plugins."""
        results = []
        dt = details or {}
        for pid, p in self.plugins.items():
            if p.enabled:
                try:
                    res = p.on_purchase_detected(user_id, product_code, dt)
                    if res:
                        results.append({"plugin_id": pid, "output": res})
                except Exception as e:
                    logger.error(f"[PluginHook Error] Plugin '{pid}' failed on_purchase: {e}")
        return results


plugin_manager = PluginManager()
