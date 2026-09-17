import os
import sys
import json
import logging
import importlib.util
import traceback
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable

logger = logging.getLogger(__name__)

PLUGINS_DIR = Path(__file__).parent / "plugins"
PLUGINS_DIR.mkdir(parents=True, exist_ok=True)


# =====================================================================
# V2 Legacy Base Classes (Backward Compatibility)
# =====================================================================

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


class BaseChannelPlugin(BasePlugin):
    """
    Extended base class for channel-type plugins (WhatsApp, Telegram, etc.).
    Channel plugins can manage external connections and have additional lifecycle hooks.
    """
    plugin_type: str = "channel"
    platform: str = "unknown"

    async def on_startup(self, config: Dict[str, Any]) -> None:
        pass

    async def on_shutdown(self) -> None:
        pass

    async def send_message(self, recipient: str, text: str, **kwargs) -> Optional[Dict[str, Any]]:
        return None

    def get_status(self) -> Dict[str, Any]:
        return {
            "plugin_id": self.plugin_id,
            "platform": self.platform,
            "connected": False,
            "status": "not_implemented",
        }

    def get_config_schema(self) -> List[Dict[str, Any]]:
        return []


# =====================================================================
# V3 Chrome-like Extension Engine Architecture
# =====================================================================

class ExtensionV3:
    """
    Represents a full v3 Chrome-like extension.
    Contains metadata, isolated config, backend router, and dynamic UI declarations.
    """
    def __init__(self, dir_path: Path, manifest: Dict[str, Any]):
        self.dir_path = dir_path
        self.manifest = manifest
        self.id: str = manifest.get("id", dir_path.name)
        self.name: str = manifest.get("name", dir_path.name)
        self.version: str = manifest.get("version", "1.0.0")
        self.description: str = manifest.get("description", "")
        self.author: str = manifest.get("author", "Community")
        self.icon: str = manifest.get("icon", "puzzle")  # Lucide icon name
        self.entrypoint: str = manifest.get("entrypoint", "backend.py")
        self.permissions: List[str] = manifest.get("permissions", [])
        self.enabled: bool = manifest.get("enabled", True)

        # Isolated config file path
        self.config_path: Path = dir_path / "config.json"

        # UI Declarations from Manifest
        self.ui_spec: Dict[str, Any] = manifest.get("ui", {})
        self.tab_spec: Optional[Dict[str, Any]] = self.ui_spec.get("tab")
        self.settings_fields: List[Dict[str, Any]] = self.ui_spec.get("settings_fields", [])
        self.topbar_badges: List[Dict[str, Any]] = self.ui_spec.get("topbar_badges", [])
        self.widgets: List[Dict[str, Any]] = self.ui_spec.get("widgets", [])
        self.custom_scripts: List[str] = self.ui_spec.get("scripts", [])
        self.custom_styles: List[str] = self.ui_spec.get("styles", [])

        # Backend module and router instances
        self.module = None
        self.router = None
        self.plugin_instance: Optional[BasePlugin] = None

    def get_config(self) -> Dict[str, Any]:
        """Load isolated configuration, merging with field defaults."""
        data = {}
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as e:
                logger.error(f"[ExtensionV3:{self.id}] Failed to read config: {e}")

        # Populate defaults for any missing keys
        for field in self.settings_fields:
            key = field.get("key")
            if key and key not in data and "default" in field:
                data[key] = field["default"]

        return data

    def save_config(self, new_data: Dict[str, Any]) -> bool:
        """Save isolated configuration for this extension."""
        try:
            current = self.get_config()
            current.update(new_data)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(current, f, ensure_ascii=False, indent=2)

            # Trigger hook if module has on_config_updated
            if self.module and hasattr(self.module, "on_config_updated"):
                try:
                    self.module.on_config_updated(current)
                except Exception as e:
                    logger.warning(f"[ExtensionV3:{self.id}] on_config_updated error: {e}")

            return True
        except Exception as e:
            logger.error(f"[ExtensionV3:{self.id}] Failed to save config: {e}")
            return False

    def get_rendered_tab_html(self) -> Optional[str]:
        """Read and return the HTML content of the extension's tab template."""
        if not self.tab_spec:
            return None

        # Template can be an inline HTML string or a relative file path
        if "html" in self.tab_spec:
            return self.tab_spec["html"]

        template_file = self.tab_spec.get("template")
        if template_file:
            path = self.dir_path / template_file
            if path.exists():
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        return f.read()
                except Exception as e:
                    logger.error(f"[ExtensionV3:{self.id}] Failed to read tab template: {e}")
                    return f"<div class='alert alert-danger'>فشل تحميل قالب الإضافة: {e}</div>"

        return None


class ExtensionEngineV3:
    """
    M.A.R.K.E.T v3 Master Extension Engine.
    Manages Chrome-like extensions:
    - Discovery of manifests (`manifest.json` or legacy `plugin.json`)
    - Dynamic FastAPI APIRouter mounting under `/ext/{id}/*`
    - Aggregation of dynamic UI schema (Sidebar tabs, settings forms, badges)
    - Event bus dispatching across all active extensions
    """
    def __init__(self, plugins_dir: Path = PLUGINS_DIR):
        self.plugins_dir = plugins_dir
        self.extensions: Dict[str, ExtensionV3] = {}
        self.extension_states: Dict[str, bool] = {}
        self.event_listeners: Dict[str, List[Callable]] = {}

        # Legacy plugins holder
        self.legacy_plugins: Dict[str, BasePlugin] = {}

    def load_all(self):
        """Scan, parse manifests, and load all v3 extensions and legacy plugins."""
        self.extensions.clear()
        self.legacy_plugins.clear()

        # ── 1. Load V3 Directory Extensions (manifest.json or plugin.json) ──
        for subdir in self.plugins_dir.iterdir():
            if not subdir.is_dir() or subdir.name.startswith("__"):
                continue

            manifest_path = subdir / "manifest.json"
            is_v3 = True

            # Fallback to legacy plugin.json if manifest.json not found
            if not manifest_path.exists():
                manifest_path = subdir / "plugin.json"
                is_v3 = False

            if manifest_path.exists():
                try:
                    with open(manifest_path, "r", encoding="utf-8") as f:
                        manifest = json.load(f)

                    ext_id = manifest.get("id", subdir.name)
                    ext = ExtensionV3(subdir, manifest)

                    # Preserve toggle state if previously saved
                    if ext_id in self.extension_states:
                        ext.enabled = self.extension_states[ext_id]
                    else:
                        self.extension_states[ext_id] = ext.enabled

                    # Load the backend entrypoint
                    self._load_extension_backend(ext)

                    self.extensions[ext_id] = ext
                    logger.info(f"[ExtensionEngineV3] Loaded extension: '{ext.name}' (ID: {ext_id}, Enabled: {ext.enabled})")

                except Exception as e:
                    logger.error(f"[ExtensionEngineV3] Error loading extension in '{subdir.name}': {e}\n{traceback.format_exc()}")

        # ── 2. Load Legacy Single-File Plugins (*.py in plugins/) ────────────
        for file in self.plugins_dir.glob("*.py"):
            if file.name.startswith("__"):
                continue

            plugin_id = file.stem
            try:
                spec = importlib.util.spec_from_file_location(plugin_id, file)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[plugin_id] = module
                    spec.loader.exec_module(module)

                    if hasattr(module, "Plugin") and issubclass(module.Plugin, BasePlugin):
                        instance = module.Plugin()
                        instance.plugin_id = plugin_id

                        if plugin_id in self.extension_states:
                            instance.enabled = self.extension_states[plugin_id]
                        else:
                            self.extension_states[plugin_id] = instance.enabled

                        self.legacy_plugins[plugin_id] = instance
                        logger.info(f"[ExtensionEngineV3] Loaded legacy single-file plugin: '{instance.name}' ({plugin_id})")
            except Exception as e:
                logger.error(f"[ExtensionEngineV3] Failed to load legacy plugin '{file.name}': {e}")

    def _load_extension_backend(self, ext: ExtensionV3):
        """Execute the Python backend entrypoint and extract router/plugin instance."""
        entry_file = ext.dir_path / ext.entrypoint
        if not entry_file.exists():
            # Try adapter.py or server.py
            for fallback in ("backend.py", "adapter.py", "server.py", "whatsapp_plugin.py"):
                alt = ext.dir_path / fallback
                if alt.exists():
                    entry_file = alt
                    break

        if entry_file.exists() and entry_file.suffix == ".py":
            try:
                mod_name = f"plugins.{ext.dir_path.name}.{entry_file.stem}"
                spec = importlib.util.spec_from_file_location(mod_name, entry_file)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[mod_name] = module
                    spec.loader.exec_module(module)
                    ext.module = module

                    # Look for FastAPI APIRouter instance
                    if hasattr(module, "router"):
                        ext.router = getattr(module, "router")
                        logger.info(f"[ExtensionEngineV3] Found APIRouter in extension '{ext.id}'")

                    # Look for Plugin class (BasePlugin implementation)
                    if hasattr(module, "Plugin") and issubclass(module.Plugin, BasePlugin):
                        inst = module.Plugin()
                        inst.plugin_id = ext.id
                        inst.enabled = ext.enabled
                        ext.plugin_instance = inst
                        self.legacy_plugins[ext.id] = inst

            except Exception as e:
                logger.error(f"[ExtensionEngineV3:{ext.id}] Failed to execute backend '{entry_file.name}': {e}\n{traceback.format_exc()}")

        # Also load companion *_plugin.py if present
        for comp in ext.dir_path.glob("*_plugin.py"):
            try:
                comp_mod_name = f"plugins.{ext.dir_path.name}.{comp.stem}"
                comp_spec = importlib.util.spec_from_file_location(comp_mod_name, comp)
                if comp_spec and comp_spec.loader:
                    comp_mod = importlib.util.module_from_spec(comp_spec)
                    sys.modules[comp_mod_name] = comp_mod
                    comp_spec.loader.exec_module(comp_mod)

                    if hasattr(comp_mod, "Plugin") and issubclass(comp_mod.Plugin, BasePlugin):
                        comp_inst = comp_mod.Plugin()
                        comp_inst.plugin_id = ext.id
                        comp_inst.enabled = ext.enabled
                        ext.plugin_instance = comp_inst
                        self.legacy_plugins[ext.id] = comp_inst
            except Exception as e:
                logger.warning(f"[ExtensionEngineV3:{ext.id}] Companion plugin '{comp.name}' error: {e}")

    def mount_routers(self, app):
        """Mount all extension APIRouters dynamically into the main FastAPI application."""
        for ext_id, ext in self.extensions.items():
            if ext.router:
                prefix = f"/ext/{ext_id}"
                try:
                    # Check if already included
                    already_mounted = any(getattr(r, "path", "").startswith(prefix) for r in app.routes)
                    if not already_mounted:
                        app.include_router(ext.router, prefix=prefix, tags=[ext.name])
                        logger.info(f"[ExtensionEngineV3] Mounted routes for '{ext_id}' at '{prefix}'")
                except Exception as e:
                    logger.error(f"[ExtensionEngineV3] Failed to mount router for '{ext_id}': {e}")

    def get_ui_schema(self) -> Dict[str, Any]:
        """
        Aggregate full UI schema for the frontend Shell:
        - Tabs: Dynamic navigation tabs and rendered HTML panels
        - Settings: Dynamic form input fields and current values
        - Badges: Topbar status indicators
        - Widgets: Dashboard widget slots
        """
        schema = {
            "tabs": [],
            "settings_sections": [],
            "topbar_badges": [],
            "widgets": [],
            "scripts": [],
            "styles": [],
        }

        for ext_id, ext in self.extensions.items():
            if not ext.enabled:
                continue

            # 1. Tab injection
            if ext.tab_spec:
                rendered_html = ext.get_rendered_tab_html()
                schema["tabs"].append({
                    "extension_id": ext.id,
                    "tab_id": ext.tab_spec.get("id", f"tab-ext-{ext.id}"),
                    "title": ext.tab_spec.get("title", ext.name),
                    "icon": ext.tab_spec.get("icon", ext.icon),
                    "html": rendered_html or f"<div class='p-4'><h3>{ext.name}</h3><p>{ext.description}</p></div>",
                    "order": ext.tab_spec.get("order", 100),
                })

            # 2. Dynamic Settings fields
            if ext.settings_fields:
                schema["settings_sections"].append({
                    "extension_id": ext.id,
                    "title": ext.name,
                    "icon": ext.icon,
                    "description": ext.description,
                    "fields": ext.settings_fields,
                    "values": ext.get_config(),
                })

            # 3. Topbar Badges
            for badge in ext.topbar_badges:
                schema["topbar_badges"].append({
                    "extension_id": ext.id,
                    "badge_id": badge.get("id", f"badge-{ext.id}"),
                    "html": badge.get("html", ""),
                    "endpoint": badge.get("endpoint", f"/ext/{ext.id}/status"),
                })

            # 4. Widgets
            for widget in ext.widgets:
                schema["widgets"].append({
                    "extension_id": ext.id,
                    "target_tab": widget.get("target_tab", "tab-settings"),
                    "html": widget.get("html", ""),
                })

        return schema

    def set_extension_state(self, ext_id: str, enabled: bool) -> bool:
        """Enable or disable an extension by ID."""
        self.extension_states[ext_id] = enabled
        found = False

        if ext_id in self.extensions:
            self.extensions[ext_id].enabled = enabled
            if self.extensions[ext_id].plugin_instance:
                self.extensions[ext_id].plugin_instance.enabled = enabled
            found = True

        if ext_id in self.legacy_plugins:
            self.legacy_plugins[ext_id].enabled = enabled
            found = True

        logger.info(f"[ExtensionEngineV3] Extension '{ext_id}' toggled to: {enabled}")
        return found

    def list_all(self) -> List[Dict[str, Any]]:
        """List all extensions and legacy plugins in standard structured format."""
        result = []
        seen = set()

        for ext_id, ext in self.extensions.items():
            result.append({
                "id": ext.id,
                "plugin_id": ext.id,
                "name": ext.name,
                "version": ext.version,
                "description": ext.description,
                "author": ext.author,
                "icon": ext.icon,
                "enabled": ext.enabled,
                "is_v3": True,
                "has_tab": ext.tab_spec is not None,
                "has_settings": len(ext.settings_fields) > 0,
                "has_router": ext.router is not None,
                "permissions": ext.permissions,
                "ui_snippet": ext.plugin_instance.get_ui_snippet() if ext.plugin_instance else None,
            })
            seen.add(ext_id)

        for pid, p in self.legacy_plugins.items():
            if pid in seen:
                continue
            ui_snip = None
            if hasattr(p, "get_ui_snippet"):
                try:
                    ui_snip = p.get_ui_snippet()
                except Exception:
                    pass

            result.append({
                "id": pid,
                "plugin_id": pid,
                "name": p.name,
                "version": p.version,
                "description": p.description,
                "author": p.author,
                "icon": "puzzle",
                "enabled": p.enabled,
                "is_v3": False,
                "has_tab": False,
                "has_settings": False,
                "has_router": False,
                "permissions": [],
                "ui_snippet": ui_snip,
            })

        return result


# =====================================================================
# Unified PluginManager Interface (Backward Compatibility Bridge)
# =====================================================================

class PluginManager:
    """
    Unified manager bridge connecting legacy calls to ExtensionEngineV3.
    """
    def __init__(self):
        self.engine = ExtensionEngineV3()
        self.load_plugins()

    def load_plugins(self):
        self.engine.load_all()

    @property
    def plugins(self) -> Dict[str, BasePlugin]:
        return self.engine.legacy_plugins

    @property
    def plugin_states(self) -> Dict[str, bool]:
        return self.engine.extension_states

    @property
    def channel_plugins(self) -> Dict[str, Any]:
        return self.engine.extensions

    def list_plugins(self) -> List[Dict[str, Any]]:
        return self.engine.list_all()

    def get_channel_plugins(self) -> List[Dict[str, Any]]:
        channels = []
        for ext_id, ext in self.engine.extensions.items():
            channels.append({
                "plugin_id": ext.id,
                "name": ext.name,
                "description": ext.description,
                "enabled": ext.enabled,
                "plugin_type": ext.manifest.get("plugin_type", "channel"),
                "has_adapter": ext.module is not None,
                "entrypoint": ext.entrypoint,
            })
        return channels

    def set_plugin_state(self, plugin_id: str, enabled: bool):
        self.engine.set_extension_state(plugin_id, enabled)

    def trigger_message_hook(self, user_id: str, message: str) -> List[Dict[str, Any]]:
        results = []
        for pid, p in self.engine.legacy_plugins.items():
            if p.enabled:
                try:
                    res = p.on_message_received(user_id, message)
                    if res:
                        results.append({"plugin_id": pid, "output": res})
                except Exception as e:
                    logger.error(f"[PluginHook Error] Plugin '{pid}' failed on_message: {e}")
        return results

    def trigger_reply_hook(self, user_id: str, prompt: str, reply: str, metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        results = []
        meta = metadata or {}
        for pid, p in self.engine.legacy_plugins.items():
            if p.enabled:
                try:
                    res = p.on_reply_generated(user_id, prompt, reply, meta)
                    if res:
                        results.append({"plugin_id": pid, "output": res})
                except Exception as e:
                    logger.error(f"[PluginHook Error] Plugin '{pid}' failed on_reply: {e}")
        return results

    def trigger_purchase_hook(self, user_id: str, product_code: str, details: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        results = []
        dt = details or {}
        for pid, p in self.engine.legacy_plugins.items():
            if p.enabled:
                try:
                    res = p.on_purchase_detected(user_id, product_code, dt)
                    if res:
                        results.append({"plugin_id": pid, "output": res})
                except Exception as e:
                    logger.error(f"[PluginHook Error] Plugin '{pid}' failed on_purchase: {e}")
        return results

    def get_ui_schema(self) -> Dict[str, Any]:
        return self.engine.get_ui_schema()

    def mount_extension_routers(self, app):
        self.engine.mount_routers(app)


plugin_manager = PluginManager()
extension_engine = plugin_manager.engine
