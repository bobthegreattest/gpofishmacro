import tkinter as tk
import tkinter.ttk as ttk
import threading
import time
import os
import signal
import json
import customtkinter as ctk
from pynput import mouse, keyboard as pkb

# Set CustomTkinter appearance mode
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")
from pynput.mouse import Button, Controller as MouseController
from PIL import Image
import numpy as np
import mss

# Tesseract OCR for devil fruit text detection
try:
    import pytesseract
    from PIL import Image
    TESSERACT_AVAILABLE = True
    print("PyTesseract loaded successfully!")
except ImportError as e:
    TESSERACT_AVAILABLE = False
    print(f"WARNING: PyTesseract import failed: {e}")
    print("Install with: pip install pytesseract")
    print("Also install Tesseract: brew install tesseract")

# Quartz/CoreGraphics for reliable keyboard input
try:
    import Quartz
    from AppKit import NSWindow, NSColor, NSBezierPath, NSGraphicsContext, NSApp, NSApplication, NSWorkspace, NSRunningApplication
    from Foundation import NSPoint, NSMakeRect
    QUARTZ_AVAILABLE = True
    print("PyObjC loaded successfully!")
except ImportError as e:
    QUARTZ_AVAILABLE = False
    print(f"WARNING: PyObjC import failed: {e}")

# CGEvent keyboard event helper
def press_key(key_code):
    """Press a key using CGEvent (more reliable for games like Roblox)"""
    try:
        if not QUARTZ_AVAILABLE:
            return False
        
        # Create key down event
        event_down = Quartz.CGEventCreateKeyboardEvent(None, key_code, True)
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, event_down)
        return True
    except Exception as e:
        print(f"[DEBUG] CGEvent press error: {e}")
        return False

def release_key(key_code):
    """Release a key using CGEvent"""
    try:
        if not QUARTZ_AVAILABLE:
            return False
        
        # Create key up event
        event_up = Quartz.CGEventCreateKeyboardEvent(None, key_code, False)
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, event_up)
        return True
    except Exception as e:
        print(f"[DEBUG] CGEvent release error: {e}")
        return False

# Key code mapping for number keys
KEY_CODES = {
    '0': 0x1D, '1': 0x12, '2': 0x13, '3': 0x14, '4': 0x15,
    '5': 0x17, '6': 0x16, '7': 0x1A, '8': 0x1C, '9': 0x19,
    'shift': 0x38, 'backspace': 0x33,
    '=': 0x18,  # Key code for "=" and "+" key
}

DISPLAY_KEYS = {
    "bracketleft": "[",
    "bracketright": "]",
    "f1": "F1",
    "f2": "F2",
    "f3": "F3",
    "f4": "F4",
    "f5": "F5",
}

SETTINGS_FILE = "GPOsettings.json"

 
class OverlaySelector:
    """Creates draggable/resizable overlay windows for bar and drop layouts.
    Uses the same proven implementation as OverlayManager."""
    
    def __init__(self, parent, bar_coords, drop_coords, callback):
        self.callback = callback
        self.bar_window = None
        self.drop_window = None
        self.bar_frame = None
        self.drop_frame = None
        self.bar_label = None
        self.drop_label = None
        
        # Shared drag data (same pattern as OverlayManager)
        self.drag_data = {
            'bar': {'x': 0, 'y': 0, 'resize_edge': None, 'start_width': 0, 
                    'start_height': 0, 'start_x': 0, 'start_y': 0},
            'drop': {'x': 0, 'y': 0, 'resize_edge': None, 'start_width': 0, 
                     'start_height': 0, 'start_x': 0, 'start_y': 0}
        }
        
        screen_width = parent.winfo_screenwidth()
        screen_height = parent.winfo_screenheight()
        
        # Bar layout overlay (blue)
        if bar_coords:
            x1, y1, x2, y2 = bar_coords["x1"], bar_coords["y1"], bar_coords["x2"], bar_coords["y2"]
        else:
            x1, y1 = int(screen_width * 0.52461), int(screen_height * 0.29167)
            x2, y2 = int(screen_width * 0.68477), int(screen_height * 0.79097)
        
        self._create_overlay("Fishing Bar Area", x1, y1, x2, y2, "#3366CC", "bar")
        
        # Drop layout overlay (green) - positioned next to bar
        if drop_coords:
            dx1, dy1, dx2, dy2 = drop_coords["x1"], drop_coords["y1"], drop_coords["x2"], drop_coords["y2"]
        else:
            dx1, dy1 = int(screen_width * 0.75), int(screen_height * 0.2)
            dx2, dy2 = int(screen_width * 0.85), int(screen_height * 0.6)
        
        self._create_overlay("Fruit Detection Area", dx1, dy1, dx2, dy2, "#339933", "drop")
    
    def _create_overlay(self, title, x1, y1, x2, y2, bg_color, layout_type):
        """Create a single overlay window - identical to OverlayManager pattern"""
        window = tk.Toplevel(None)
        window.overrideredirect(True)
        window.attributes('-alpha', 0.6)
        window.attributes('-topmost', True)
        window.minsize(50, 50)
        
        width, height = x2 - x1, y2 - y1
        window.geometry(f"{width}x{height}+{x1}+{y1}")
        window.configure(bg=bg_color)
        
        # Frame with border
        frame = tk.Frame(window, bg=bg_color, highlightthickness=3, 
                        highlightbackground='white')
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Title label
        label = tk.Label(frame, text=title, bg=bg_color, fg='white', 
                        font=('Arial', 10, 'bold'))
        label.pack(pady=2)
        
        # Store references
        if layout_type == "bar":
            self.bar_window = window
            self.bar_frame = frame
            self.bar_label = label
        else:
            self.drop_window = window
            self.drop_frame = frame
            self.drop_label = label
        
        # Bind events - exactly like OverlayManager
        window.bind("<ButtonPress-1>", lambda e, t=layout_type: self._start_action(e, t))
        window.bind("<B1-Motion>", lambda e, t=layout_type: self._motion(e, t))
        window.bind("<Motion>", lambda e, t=layout_type: self._update_cursor(e, t))
        window.bind("<Configure>", lambda e, t=layout_type: self._on_configure(e, t))
        
        frame.bind("<ButtonPress-1>", lambda e, t=layout_type: self._start_action(e, t))
        frame.bind("<B1-Motion>", lambda e, t=layout_type: self._motion(e, t))
        frame.bind("<Motion>", lambda e, t=layout_type: self._update_cursor(e, t))
        
        label.bind("<ButtonPress-1>", lambda e, t=layout_type: self._start_action(e, t))
        label.bind("<B1-Motion>", lambda e, t=layout_type: self._motion(e, t))
        label.bind("<Motion>", lambda e, t=layout_type: self._update_cursor(e, t))
    
    def _get_window(self, layout_type):
        """Get the window for the given layout type"""
        if layout_type == "bar":
            return self.bar_window
        return self.drop_window
    
    def _get_resize_edge(self, x, y, layout_type):
        """Determine which edge/corner is being hovered for resize.
        Identical to OverlayManager implementation."""
        window = self._get_window(layout_type)
        if not window:
            return None
        
        width = window.winfo_width()
        height = window.winfo_height()
        edge_size = 10
        on_left = x < edge_size
        on_right = x > width - edge_size
        on_top = y < edge_size
        on_bottom = y > height - edge_size
        
        if on_top and on_left:
            return "nw"
        elif on_top and on_right:
            return "ne"
        elif on_bottom and on_left:
            return "sw"
        elif on_bottom and on_right:
            return "se"
        elif on_left:
            return "w"
        elif on_right:
            return "e"
        elif on_top:
            return "n"
        elif on_bottom:
            return "s"
        return None
    
    def _update_cursor(self, event, layout_type):
        """Update cursor based on hover position.
        Identical to OverlayManager implementation."""
        window = self._get_window(layout_type)
        if not window:
            return
        
        edge = self._get_resize_edge(event.x, event.y, layout_type)
        
        # Use cross-platform cursor names
        import platform
        is_mac = platform.system() == 'Darwin'
        
        if is_mac:
            # macOS cursor names
            cursor_map = {
                'nw': 'top_left_corner', 
                'ne': 'top_right_corner', 
                'sw': 'bottom_left_corner', 
                'se': 'bottom_right_corner', 
                'n': 'sb_v_double_arrow', 
                's': 'sb_v_double_arrow', 
                'e': 'sb_h_double_arrow', 
                'w': 'sb_h_double_arrow', 
                None: 'arrow'
            }
        else:
            # Windows/Linux cursor names
            cursor_map = {
                'nw': 'size_nw_se', 
                'ne': 'size_ne_sw', 
                'sw': 'size_ne_sw', 
                'se': 'size_nw_se', 
                'n': 'size_ns', 
                's': 'size_ns', 
                'e': 'size_ew', 
                'w': 'size_ew', 
                None: 'arrow'
            }
        
        try:
            window.config(cursor=cursor_map.get(edge, 'arrow'))
        except Exception:
            # Fallback to arrow cursor if specified cursor is not available
            try:
                window.config(cursor='arrow')
            except Exception:
                pass
    
    def _start_action(self, event, layout_type):
        """Start drag or resize.
        Identical to OverlayManager implementation."""
        window = self._get_window(layout_type)
        if not window:
            return
        
        # Update existing drag data dict (like OverlayManager)
        self.drag_data[layout_type]['x'] = event.x
        self.drag_data[layout_type]['y'] = event.y
        self.drag_data[layout_type]['resize_edge'] = self._get_resize_edge(event.x, event.y, layout_type)
        self.drag_data[layout_type]['start_width'] = window.winfo_width()
        self.drag_data[layout_type]['start_height'] = window.winfo_height()
        self.drag_data[layout_type]['start_x'] = window.winfo_x()
        self.drag_data[layout_type]['start_y'] = window.winfo_y()
    
    def _motion(self, event, layout_type):
        """Handle drag or resize.
        Identical to OverlayManager implementation."""
        window = self._get_window(layout_type)
        if not window:
            return
        
        data = self.drag_data[layout_type]
        edge = data['resize_edge']
        
        if edge is None:
            # Just dragging - use current position + delta (like OverlayManager)
            x = window.winfo_x() + event.x - data['x']
            y = window.winfo_y() + event.y - data['y']
            window.geometry(f'+{x}+{y}')
        else:
            # Resizing
            dx = event.x - data['x']
            dy = event.y - data['y']
            
            new_width = data['start_width']
            new_height = data['start_height']
            new_x = data['start_x']
            new_y = data['start_y']
            
            if 'e' in edge:
                new_width = max(50, data['start_width'] + dx)
            elif 'w' in edge:
                new_width = max(50, data['start_width'] - dx)
                new_x = data['start_x'] + dx
            
            if 's' in edge:
                new_height = max(50, data['start_height'] + dy)
            elif 'n' in edge:
                new_height = max(50, data['start_height'] - dy)
                new_y = data['start_y'] + dy
            
            window.geometry(f"{new_width}x{new_height}+{new_x}+{new_y}")
    
    def _on_configure(self, event, layout_type):
        """Handle window configure events."""
        pass  # Not needed for basic drag/resize functionality
    
    def close(self):
        """Close both overlays and save coordinates"""
        bar_coords = None
        drop_coords = None
        
        if self.bar_window:
            x1, y1 = self.bar_window.winfo_x(), self.bar_window.winfo_y()
            x2, y2 = x1 + self.bar_window.winfo_width(), y1 + self.bar_window.winfo_height()
            bar_coords = {"x1": x1, "y1": y1, "x2": x2, "y2": y2}
            self.bar_window.destroy()
        
        if self.drop_window:
            x1, y1 = self.drop_window.winfo_x(), self.drop_window.winfo_y()
            x2, y2 = x1 + self.drop_window.winfo_width(), y1 + self.drop_window.winfo_height()
            drop_coords = {"x1": x1, "y1": y1, "x2": x2, "y2": y2}
            self.drop_window.destroy()
        
        self.callback(bar_coords, drop_coords)


class MacroApp:
    def __init__(self, root):
        self.root = root
        self.root.title("GPO Fishing Macro")
        self.root.geometry("500x400")
        self.root.minsize(400, 300)

        # Hotkeys
        self.hotkeys = {
            "start_stop": "bracketleft",
            "toggle_area": "bracketright",
            "exit": "f3"
        }

        self.settings = self.load_settings()
        self.start_stop_state = False
        self.toggle_area_state = False
        self.main_loop_running = False
        self.stop_requested = False  # Flag for instant stop when hotkey pressed
        
        # Mouse controller for clicking
        self.mouse_controller = MouseController()
        self.is_holding_click = False
        
        # Keyboard controller for key presses
        self.keyboard = pkb.Controller()
        
        # Water point for casting
        self.water_point = self.settings.get("water_point", None)
        self.setting_water_point = False
        
        # Auto Buy Common Bait points
        self.left_point = self.settings.get("left_point", None)
        self.middle_point = self.settings.get("middle_point", None)
        self.right_point = self.settings.get("right_point", None)
        self.loops_per_purchase = self.settings.get("loops_per_purchase", 100)
        self.setting_left_point = False
        self.setting_middle_point = False
        self.setting_right_point = False

        # Pre-cast checkbox variables
        self.auto_buy_common_bait_var = tk.BooleanVar(value=self.settings.get("auto_buy_common_bait", True))
        self.auto_store_devil_fruit_var = tk.BooleanVar(value=self.settings.get("auto_store_devil_fruit", False))
        
        # Store Fruit Point for auto store devil fruit
        self.store_fruit_point = self.settings.get("store_fruit_point", None)
        self.setting_store_fruit_point = False
        
        # Store DF Area for auto store devil fruit (rectangular area selector)
        self.store_df_area = self.settings.get("store_df_area", None)
        self.setting_store_df_area = False
        self.store_df_area_selector = None
        
        # Devil Fruit, Rod, and Store Fruit Hotkeys
        self.devil_fruit_hotkey_var = tk.IntVar(value=self.settings.get("devil_fruit_hotkey", 2))
        self.rod_hotkey_var = tk.IntVar(value=self.settings.get("rod_hotkey", 1))
        self.store_fruit_hotkey_var = tk.IntVar(value=self.settings.get("store_fruit_hotkey", 4))
        self.anything_else_hotkey_var = tk.IntVar(value=self.settings.get("anything_else_hotkey", 3))

        # Devil fruit detection settings
        self.devil_fruit_detected = False  # Flag for whether a fruit was detected in drop area
        self.last_fruit_check_time = 0  # Timestamp of last fruit check
        self.fruit_check_cooldown = 1.0  # Seconds between fruit checks
        
        # Devil fruit names for spawn detection
        self.devil_fruits = [
            'Tori', 'Mochi', 'Ope', 'Venom', 'Buddha', 'Pteranodon',
            'Smoke', 'Goru', 'Yuki', 'Yami', 'Pika', 'Magu',
            'Kage', 'Mera', 'Paw', 'Goro', 'Ito', 'Hie',
            'Suna', 'Gura', 'Zushi', 'Kira', 'Spring', 'Yomi',
            'Bomb', 'Gomu', 'Horo', 'Mero', 'Bari', 'Heal',
            'Spin', 'Suke', 'Kilo'
        ]
        
        # Create lowercase mapping for fuzzy matching
        self.devil_fruits_lower = [f.lower() for f in self.devil_fruits]

        # Initialize bar_area and drop_area from settings
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        
        # Bar layout area (original fishing area)
        if self.settings.get("bar_area"):
            self.bar_area = self.settings["bar_area"]
        else:
            self.bar_area = {
                "x1": int(screen_width * 0.52461),
                "y1": int(screen_height * 0.29167),
                "x2": int(screen_width * 0.68477),
                "y2": int(screen_height * 0.79097)
            }
        
        # Drop layout area (loot drop area)
        if self.settings.get("drop_area"):
            self.drop_area = self.settings["drop_area"]
        else:
            self.drop_area = {
                "x1": int(screen_width * 0.75),
                "y1": int(screen_height * 0.2),
                "x2": int(screen_width * 0.85),
                "y2": int(screen_height * 0.6)
            }
        
        # Keep area_box for backward compatibility
        self.area_box = self.bar_area

        # PID Controller variables
        self.kp = 0.8  # Proportional gain
        self.ki = 0.02  # Integral gain
        self.kd = 1.5  # Derivative gain
        
        # Thread management
        self.main_loop_thread = None  # Track the main loop thread
        
        self.previous_error = 0
        self.integral = 0
        self.previous_time = None
        
        # Anti-windup - limit integral to prevent it from growing too large
        self.integral_max = 100
        self.integral_min = -100
        
        # Hysteresis to prevent rapid switching
        self.switch_threshold = 2  # Only switch state if control signal crosses this threshold
        
        # Fishing state machine
        self.fishing_state = "IDLE"  # IDLE, CASTING, WAITING, FISHING
        self.cast_time = None
        self.blue_lost_time = None
        self.blue_lost_delay = 1.5  # Wait 1.5 seconds after blue disappears before recasting
        self.recast_locked = False  # Once locked, we're committed to recasting
        self.waiting_start_time = None  # Track when we entered WAITING state
        self.fishing_loop_count = 0  # Counter for loops between auto-buy
        self.waiting_timeout = self.settings.get("waiting_timeout", 15)  # Max seconds to wait for blue to appear before recasting

        # Area selector
        self.area_selector_active = False
        self.selector_window = None
        self.start_pos = None
        self.end_pos = None
        self.mouse_listener = None
        self.overlay_canvas = None
        self.area_selector = None
        
        # DEBUG: Arrow overlay for visual debugging
        self.debug_mode = True  # SET TO False TO REMOVE ALL DEBUG FEATURES
        
        # Simple approach - just print to terminal instead of overlay
        # Quartz is too complex and causes crashes

        # Debug flag for scroll behavior (set before build_gui so it's available during tab building)
        self.debug_scroll = False  # Set to True for scroll debugging output

        # Build GUI
        self.build_gui()

        # Initialize MSS for fast screenshots
        self.sct = mss.mss()

        # Start global hotkey listener
        self.hotkey_listener = pkb.Listener(on_press=self.on_hotkey_press)
        self.hotkey_listener.start()

        # Set up click to unfocus spinbox (click elsewhere to deselect)
        self.root.bind("<Button-1>", self.on_root_click)
        self.setup_spinbox_unfocus()

        # Migrate old store_df_area format to new format (after GUI is built so all widgets exist)
        self.migrate_store_df_area_format()

    def migrate_store_df_area_format(self):
        """Convert old store_df_area format to new format if needed"""
        self.store_df_area = self.settings.get("store_df_area", None)
        
        # Convert old format (start/end arrays) to new format (x1, y1, x2, y2)
        if self.store_df_area and isinstance(self.store_df_area, dict):
            if "start" in self.store_df_area and "end" in self.store_df_area:
                # Old format - convert to new format
                s = self.store_df_area["start"]
                e = self.store_df_area["end"]
                self.store_df_area = {
                    "x1": min(s[0], e[0]),
                    "y1": min(s[1], e[1]),
                    "x2": max(s[0], e[0]),
                    "y2": max(s[1], e[1])
                }
                # Save the converted format
                self.settings["store_df_area"] = self.store_df_area
                self.save_settings()

    # Settings
    def load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r") as f:
                    return json.load(f)
            except:
                return {"area": None}
        return {"area": None}
    
    def interruptible_sleep(self, seconds):
        """Sleep that can be interrupted by stop_requested flag.
        Returns True if interrupted, False if completed normally."""
        start_time = time.time()
        while time.time() - start_time < seconds:
            if self.stop_requested:
                return True  # Was interrupted
            time.sleep(0.01)  # Check every 10ms
        return False  # Completed normally

    def save_settings(self):
        # Update checkbox states before saving
        self.settings["auto_buy_common_bait"] = self.auto_buy_common_bait_var.get()
        self.settings["auto_store_devil_fruit"] = self.auto_store_devil_fruit_var.get()
        self.settings["loops_per_purchase"] = self.loops_per_purchase_var.get()
        self.settings["devil_fruit_hotkey"] = self.devil_fruit_hotkey_var.get()
        self.settings["rod_hotkey"] = self.rod_hotkey_var.get()
        self.settings["store_fruit_hotkey"] = self.store_fruit_hotkey_var.get()
        self.settings["anything_else_hotkey"] = self.anything_else_hotkey_var.get()
        self.settings["waiting_timeout"] = self.waiting_timeout
        
        with open(SETTINGS_FILE, "w") as f:
            json.dump(self.settings, f, indent=4)

    # GUI
    def build_gui(self):
        # Create CTk frame for header
        header_frame = ctk.CTkFrame(self.root, fg_color="black")
        header_frame.pack(fill=tk.X, padx=10, pady=10)

        # Title label using CTkLabel
        title_label = ctk.CTkLabel(
            header_frame, 
            text="GPO FISHING MACRO CONTROLS", 
            font=("Arial", 14, "bold"), 
            text_color="white"
        )
        title_label.pack(side=tk.LEFT, padx=5)

        # Status label using CTkLabel
        self.status_label = ctk.CTkLabel(
            header_frame, 
            text="STOPPED", 
            font=("Arial", 12, "bold"), 
            text_color="red"
        )
        self.status_label.pack(side=tk.RIGHT, padx=5)

        # Always on top checkbox using CTkCheckBox
        self.always_on_top_var = tk.BooleanVar(value=True)
        always_on_top_check = ctk.CTkCheckBox(
            header_frame, 
            text="Always On Top", 
            variable=self.always_on_top_var,
            command=self.toggle_always_on_top, 
            text_color="white",
            fg_color="#3B8ED0",
            border_color="white",
            hover_color="#3B7ED0"
        )
        always_on_top_check.pack(side=tk.RIGHT, padx=5)
        
        # Apply always on top setting on startup
        self.root.attributes("-topmost", self.always_on_top_var.get())

        # Create CTkTabview for tabs
        self.notebook = ctk.CTkTabview(self.root, fg_color="#2b2b2b")
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Add tabs
        general_tab = self.notebook.add("General")
        casting_tab = self.notebook.add("Pre-cast")
        postcast_tab = self.notebook.add("Post-cast")
        
        # Set tab colors - removed unsupported tabs_colors and tabs_label_color
        # CustomTkinter CTkTabview doesn't support these parameters
        
        # Build each tab
        self.build_general_tab(general_tab)
        self.build_casting_tab(casting_tab)
        self.build_postcast_tab(postcast_tab)
        
        # Track current canvas for scroll handling
        self.current_canvas = None
        
        # NOTE: _setup_unified_scroll_handlers() removed - CTkScrollableFrame handles scrolling automatically
    
    def _setup_unified_scroll_handlers(self):
        """Set up unified scroll handlers that work anywhere on the GUI"""
        
        # Scroll cooldown to prevent spasms at boundaries
        self._scroll_cooldown = False
        self._scroll_cooldown_duration = 200  # milliseconds to block scroll after hitting boundary
        
        def _find_scroll_target(x, y):
            """Find the scrollable widget under the mouse position by traversing widget hierarchy"""
            # Get widget at the given coordinates
            widget = self.root.winfo_containing(x, y)
            
            if widget is None:
                return None
            
            # Traverse up the widget hierarchy to find a scrollable widget
            # Look for canvas with yscrollcommand or scrollbar
            while widget:
                # Check if this widget is a canvas with scrollregion (indicating it's scrollable)
                if isinstance(widget, tk.Canvas):
                    scrollregion = widget.cget('scrollregion')
                    if scrollregion and scrollregion != "":
                        # Get dimensions to verify it actually needs scrolling
                        try:
                            sr = list(map(int, scrollregion.split() if isinstance(scrollregion, str) else scrollregion))
                            content_height = sr[3] - sr[1]
                            widget_height = widget.winfo_height()
                            if content_height > widget_height:
                                return widget
                        except:
                            pass
                
                # Check for Frame with scrollable Canvas as child
                if isinstance(widget, tk.Frame):
                    # Check if this frame contains a canvas that's scrollable
                    for child in widget.winfo_children():
                        if isinstance(child, tk.Canvas):
                            scrollregion = child.cget('scrollregion')
                            if scrollregion and scrollregion != "":
                                try:
                                    sr = list(map(int, scrollregion.split() if isinstance(scrollregion, str) else scrollregion))
                                    content_height = sr[3] - sr[1]
                                    child_height = child.winfo_height()
                                    if content_height > child_height:
                                        return child
                                except:
                                    pass
                
                widget = widget.master
            
            return None
        
        def _get_scroll_bounds(canvas):
            """Get current scroll position and max position for a canvas"""
            if canvas is None:
                return None, None
            
            canvas.update_idletasks()
            
            scrollregion = canvas.cget('scrollregion')
            if scrollregion == "":
                scrollregion = canvas.bbox("all")
                if scrollregion:
                    canvas.configure(scrollregion=scrollregion)
            
            if not scrollregion:
                return None, None
            
            sr = list(map(int, scrollregion.split() if isinstance(scrollregion, str) else scrollregion))
            content_height = sr[3] - sr[1]
            canvas_height = canvas.winfo_height()
            
            visible_fraction = canvas_height / content_height if content_height > 0 else 1
            max_pos = max(0, 1 - visible_fraction)
            current_pos = canvas.yview()[0]
            
            return current_pos, max_pos
        
        def _on_mousewheel(event):
            """Handle mouse wheel scrolling for the widget under the mouse"""
            # Check scroll cooldown - block if recently hit a boundary
            if self._scroll_cooldown:
                return "break"
            
            # Get screen coordinates for widget lookup
            screen_x = self.root.winfo_pointerx()
            screen_y = self.root.winfo_pointery()
            
            # Find the scrollable widget under the mouse
            canvas = _find_scroll_target(screen_x, screen_y)
            
            if canvas is None:
                return None
            
            current_pos, max_pos = _get_scroll_bounds(canvas)
            if current_pos is None or max_pos is None:
                return None
            
            # On macOS, trackpad scrolling has inverted direction
            delta = -event.delta
            
            if abs(delta) >= 10:
                # Mouse wheel with detents
                scroll_amount = int(delta / 120)
            else:
                # Trackpad gesture
                scroll_amount = delta
            
            if scroll_amount == 0:
                return "break"
            
            # Calculate scroll proportion
            proportion = scroll_amount * 0.03
            
            # Determine scroll direction
            scroll_down = proportion > 0
            
            # Strict boundary check - use a clear threshold for bottom detection
            if scroll_down:
                # Trying to scroll down - check if at bottom
                # Use a threshold of 5% to clearly detect bottom
                bottom_threshold = max(0.05, max_pos * 0.95)
                if current_pos >= bottom_threshold:
                    # At bottom - clamp and enable cooldown to prevent spasms
                    canvas.yview_moveto(max_pos)
                    self._scroll_cooldown = True
                    self.root.after(self._scroll_cooldown_duration, 
                                   lambda: setattr(self, '_scroll_cooldown', False))
                    return "break"
            else:
                # Trying to scroll up - check if at top
                if current_pos <= 0.01:
                    return "break"
            
            # Calculate new position
            new_pos = current_pos + proportion
            
            # Clamp to valid range - use exact max_pos for cleaner behavior
            new_pos = max(0.0, min(max_pos, new_pos))
            
            # Apply scroll
            canvas.yview_moveto(new_pos)
            
            return "break"
        
        def _on_button_4(event):
            """Handle Button-4 (scroll up) for Linux/Unix"""
            # Get screen coordinates for widget lookup
            screen_x = self.root.winfo_pointerx()
            screen_y = self.root.winfo_pointery()
            
            # Find the scrollable widget under the mouse
            canvas = _find_scroll_target(screen_x, screen_y)
            
            if canvas is None:
                return None
            
            current_pos, max_pos = _get_scroll_bounds(canvas)
            if current_pos is None:
                return None
            
            # Block if at top
            if current_pos <= 0.01:
                return "break"
            
            # Scroll up
            new_pos = max(0.0, current_pos - 0.08)
            canvas.yview_moveto(new_pos)
            
            return "break"
        
        def _on_button_5(event):
            """Handle Button-5 (scroll down) for Linux/Unix"""
            # Check scroll cooldown - block if recently hit a boundary
            if self._scroll_cooldown:
                return "break"
            
            # Get screen coordinates for widget lookup
            screen_x = self.root.winfo_pointerx()
            screen_y = self.root.winfo_pointery()
            
            # Find the scrollable widget under the mouse
            canvas = _find_scroll_target(screen_x, screen_y)
            
            if canvas is None:
                return None
            
            current_pos, max_pos = _get_scroll_bounds(canvas)
            if current_pos is None or max_pos is None:
                return None
            
            # Block if at bottom - use threshold for clean stop
            bottom_threshold = max(0.05, max_pos * 0.95)
            if current_pos >= bottom_threshold:
                canvas.yview_moveto(max_pos)
                # Enable cooldown to prevent spasms
                self._scroll_cooldown = True
                self.root.after(self._scroll_cooldown_duration, 
                               lambda: setattr(self, '_scroll_cooldown', False))
                return "break"
            
            # Scroll down
            new_pos = min(max_pos, current_pos + 0.08)
            canvas.yview_moveto(new_pos)
            
            return "break"
        
        # Bind to mouse wheel events at application level
        self.root.bind("<MouseWheel>", _on_mousewheel)
        
        # Also support Button-4 and Button-5 for Linux/Unix
        self.root.bind("<Button-4>", _on_button_4)
        self.root.bind("<Button-5>", _on_button_5)
    
    def on_tab_changed(self, event):
        """Handle tab change to update which canvas should be scrolled"""
        # Get the current tab index
        current_tab_index = self.notebook.index(self.notebook.select())
        
        # Update current_canvas based on which tab is selected
        if current_tab_index == 0 and hasattr(self, 'general_canvas') and self.general_canvas:
            self.current_canvas = self.general_canvas
            # Force update scrollregion for accurate scrolling check
            self.current_canvas.update_idletasks()
            scrollregion = self.current_canvas.bbox("all")
            if scrollregion:
                self.current_canvas.configure(scrollregion=scrollregion)
        elif current_tab_index == 1 and hasattr(self, 'casting_canvas') and self.casting_canvas:
            self.current_canvas = self.casting_canvas
            # Force update scrollregion for accurate scrolling check
            self.current_canvas.update_idletasks()
            scrollregion = self.current_canvas.bbox("all")
            if scrollregion:
                self.current_canvas.configure(scrollregion=scrollregion)
    
    def build_general_tab(self, parent):
        # Create CTkScrollableFrame with padding to avoid black borders
        scrollable_frame = ctk.CTkScrollableFrame(
            parent, 
            fg_color="#f0f0f0",
            label_text="Controls"
        )
        scrollable_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Buttons
        self.buttons = {}
        button_data = [
            ("start_stop", "Start/Stop"),
            ("toggle_area", "Change Area"),
        ]
        
        row = 0
        for action, label in button_data:
            display_key = DISPLAY_KEYS.get(self.hotkeys[action], 
                                          self.hotkeys[action].upper())
            # Use unique parameter name to avoid lambda scoping bug
            self.buttons[action] = ctk.CTkButton(
                scrollable_frame, 
                text=f"{label} ({display_key})",
                command=lambda act=action: self.handle_button_press(act), 
                width=200,
                height=40,
                font=("Arial", 11)
            )
            self.buttons[action].grid(row=row, column=0, padx=10, pady=10, sticky="ew")

            rebind_button = ctk.CTkButton(
                scrollable_frame, 
                text="Rebind",
                command=lambda act=action: self.change_hotkey(act), 
                width=80,
                height=40,
                font=("Arial", 11)
            )
            rebind_button.grid(row=row, column=1, padx=10, pady=10, sticky="ew")
            row += 1

        display_key = DISPLAY_KEYS.get(self.hotkeys["exit"], 
                                      self.hotkeys["exit"].upper())
        self.buttons["exit"] = ctk.CTkButton(
            scrollable_frame, 
            text=f"Exit ({display_key})", 
            command=self.exit_app,
            width=200,
            height=40,
            fg_color="#DC143C",
            hover_color="#B22222",
            font=("Arial", 11)
        )
        self.buttons["exit"].grid(row=row, column=0, padx=10, pady=10, sticky="ew")

        rebind_exit = ctk.CTkButton(
            scrollable_frame, 
            text="Rebind", 
            command=lambda: self.change_hotkey("exit"),
            width=80,
            height=40,
            font=("Arial", 11)
        )
        rebind_exit.grid(row=row, column=1, padx=10, pady=10, sticky="ew")

        scrollable_frame.columnconfigure(0, weight=1)
        scrollable_frame.columnconfigure(1, weight=0)
    
    def build_casting_tab(self, parent):
        # Use CTkScrollableFrame for automatic scrolling
        scrollable_frame = ctk.CTkScrollableFrame(
            parent, 
            label_text="Pre-cast Controls",
            fg_color="#2b2b2b"
        )
        scrollable_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Set Water Point section
        water_frame = ctk.CTkFrame(
            scrollable_frame,
            fg_color="#333333"
        )
        water_frame.pack(fill='x', padx=20, pady=10)
        
        # Section title
        ctk.CTkLabel(
            water_frame,
            text="Water Point",
            font=("Arial", 12, "bold"),
            text_color="white"
        ).pack(pady=(10, 5))
        
        # Set Water Point button
        self.water_point_button = ctk.CTkButton(
            water_frame,
            text="Set Water Point",
            command=self.set_water_point,
            width=200,
            height=35,
            font=("Arial", 11)
        )
        self.water_point_button.pack(pady=10)
        
        # Display current water point
        self.water_point_label = ctk.CTkLabel(
            water_frame,
            text=f"Current: {self.water_point if self.water_point else 'Not Set'}",
            font=("Arial", 10),
            text_color="lightgray"
        )
        self.water_point_label.pack(pady=5)
        
        # Auto Buy Common Bait section
        self.auto_buy_frame = ctk.CTkFrame(
            scrollable_frame,
            fg_color="#333333"
        )
        self.auto_buy_frame.pack(fill='x', padx=20, pady=10)
        
        # Section title
        ctk.CTkLabel(
            self.auto_buy_frame,
            text="Auto Buy Common Bait",
            font=("Arial", 12, "bold"),
            text_color="white"
        ).pack(pady=(10, 5))
        
        # Checkbox inside the section
        auto_buy_checkbox_inner = ctk.CTkCheckBox(
            self.auto_buy_frame,
            text="Enable Auto Buy",
            variable=self.auto_buy_common_bait_var,
            command=self.toggle_auto_buy_section,
            text_color="white",
            fg_color="#3B8ED0",
            border_color="white",
            hover_color="#3B7ED0"
        )
        auto_buy_checkbox_inner.pack(pady=10, anchor='w', padx=15)
        
        # Content frame for auto buy (shown/hidden based on checkbox)
        self.auto_buy_content_frame = ctk.CTkFrame(self.auto_buy_frame, fg_color="#333333")
        
        # Left Point section
        left_point_frame = ctk.CTkFrame(self.auto_buy_content_frame, fg_color="#333333")
        left_point_frame.pack(fill='x', padx=10, pady=5)
        
        self.left_point_button = ctk.CTkButton(
            left_point_frame,
            text="Set Left Point",
            command=self.set_left_point,
            width=150,
            height=30,
            font=("Arial", 10)
        )
        self.left_point_button.pack(side=tk.LEFT, padx=5)
        
        self.left_point_label = ctk.CTkLabel(
            left_point_frame,
            text=f"Current: {self.left_point if self.left_point else 'Not Set'}",
            font=("Arial", 10),
            text_color="lightgray"
        )
        self.left_point_label.pack(side=tk.LEFT, padx=10)
        
        # Middle Point section
        middle_point_frame = ctk.CTkFrame(self.auto_buy_content_frame, fg_color="#333333")
        middle_point_frame.pack(fill='x', padx=10, pady=5)
        
        self.middle_point_button = ctk.CTkButton(
            middle_point_frame,
            text="Set Middle Point",
            command=self.set_middle_point,
            width=150,
            height=30,
            font=("Arial", 10)
        )
        self.middle_point_button.pack(side=tk.LEFT, padx=5)
        
        self.middle_point_label = ctk.CTkLabel(
            middle_point_frame,
            text=f"Current: {self.middle_point if self.middle_point else 'Not Set'}",
            font=("Arial", 10),
            text_color="lightgray"
        )
        self.middle_point_label.pack(side=tk.LEFT, padx=10)
        
        # Right Point section
        right_point_frame = ctk.CTkFrame(self.auto_buy_content_frame, fg_color="#333333")
        right_point_frame.pack(fill='x', padx=10, pady=5)
        
        self.right_point_button = ctk.CTkButton(
            right_point_frame,
            text="Set Right Point",
            command=self.set_right_point,
            width=150,
            height=30,
            font=("Arial", 10)
        )
        self.right_point_button.pack(side=tk.LEFT, padx=5)
        
        self.right_point_label = ctk.CTkLabel(
            right_point_frame,
            text=f"Current: {self.right_point if self.right_point else 'Not Set'}",
            font=("Arial", 10),
            text_color="lightgray"
        )
        self.right_point_label.pack(side=tk.LEFT, padx=10)
        
        # Loops Per Purchase section
        loops_frame = ctk.CTkFrame(self.auto_buy_content_frame, fg_color="#333333")
        loops_frame.pack(fill='x', padx=10, pady=5)
        
        loops_label = ctk.CTkLabel(
            loops_frame,
            text="Loops Per Purchase:",
            font=("Arial", 10),
            text_color="white"
        )
        loops_label.pack(side=tk.LEFT, padx=5)
        
        self.loops_per_purchase_var = tk.IntVar(value=self.loops_per_purchase)
        loops_spinbox = tk.Spinbox(
            loops_frame,
            from_=1,
            to=10000,
            textvariable=self.loops_per_purchase_var,
            width=10,
            font=("Arial", 10),
            increment=10
        )
        loops_spinbox.pack(side=tk.LEFT, padx=5)
        
        # Pack content frame based on checkbox state
        if self.auto_buy_common_bait_var.get():
            self.auto_buy_content_frame.pack(fill='x', padx=10, pady=10)
        
        # Auto Store Devil Fruit section
        self.auto_store_frame = ctk.CTkFrame(
            scrollable_frame,
            fg_color="#333333"
        )
        self.auto_store_frame.pack(fill='x', padx=20, pady=10)
        
        # Section title
        ctk.CTkLabel(
            self.auto_store_frame,
            text="Auto Store Devil Fruit",
            font=("Arial", 12, "bold"),
            text_color="white"
        ).pack(pady=(10, 5))
        
        # Checkbox inside the section
        auto_store_checkbox_inner = ctk.CTkCheckBox(
            self.auto_store_frame,
            text="Enable Auto Store",
            variable=self.auto_store_devil_fruit_var,
            command=self.toggle_auto_store_section,
            text_color="white",
            fg_color="#3B8ED0",
            border_color="white",
            hover_color="#3B7ED0"
        )
        auto_store_checkbox_inner.pack(pady=10, anchor='w', padx=15)
        
        # Content frame for auto store (shown/hidden based on checkbox)
        self.auto_store_content_frame = ctk.CTkFrame(self.auto_store_frame, fg_color="#333333")
        
        # Store Fruit Point section
        store_fruit_frame = ctk.CTkFrame(self.auto_store_content_frame, fg_color="#333333")
        store_fruit_frame.pack(fill='x', padx=10, pady=5)
        
        self.store_fruit_point_button = ctk.CTkButton(
            store_fruit_frame,
            text="Set Store Fruit Point",
            command=self.set_store_fruit_point,
            width=150,
            height=30,
            font=("Arial", 10)
        )
        self.store_fruit_point_button.pack(side=tk.LEFT, padx=5)
        
        self.store_fruit_point_label = ctk.CTkLabel(
            store_fruit_frame,
            text=f"Point: {self.store_fruit_point if self.store_fruit_point else 'Not Set'}",
            font=("Arial", 10),
            text_color="lightgray"
        )
        self.store_fruit_point_label.pack(side=tk.LEFT, padx=10)
        
        # Devil Fruit Hotkey section
        devil_fruit_hotkey_frame = ctk.CTkFrame(self.auto_store_content_frame, fg_color="#333333")
        devil_fruit_hotkey_frame.pack(fill='x', padx=10, pady=5)
        
        devil_fruit_hotkey_label = ctk.CTkLabel(
            devil_fruit_hotkey_frame,
            text="Devil Fruit Hotkey:",
            font=("Arial", 10),
            text_color="white"
        )
        devil_fruit_hotkey_label.pack(side=tk.LEFT, padx=5)
        
        devil_fruit_hotkey_combobox = ctk.CTkComboBox(
            devil_fruit_hotkey_frame,
            values=[str(i) for i in range(10)],
            variable=self.devil_fruit_hotkey_var,
            width=60,
            font=("Arial", 10)
        )
        devil_fruit_hotkey_combobox.pack(side=tk.LEFT, padx=5)
        
        # Rod Hotkey section
        rod_hotkey_frame = ctk.CTkFrame(self.auto_store_content_frame, fg_color="#333333")
        rod_hotkey_frame.pack(fill='x', padx=10, pady=5)
        
        rod_hotkey_label = ctk.CTkLabel(
            rod_hotkey_frame,
            text="Rod Hotkey:",
            font=("Arial", 10),
            text_color="white"
        )
        rod_hotkey_label.pack(side=tk.LEFT, padx=5)
        
        rod_hotkey_combobox = ctk.CTkComboBox(
            rod_hotkey_frame,
            values=[str(i) for i in range(10)],
            variable=self.rod_hotkey_var,
            width=60,
            font=("Arial", 10)
        )
        rod_hotkey_combobox.pack(side=tk.LEFT, padx=5)
        
        # Store Fruit Hotkey section
        store_fruit_hotkey_frame = ctk.CTkFrame(self.auto_store_content_frame, fg_color="#333333")
        store_fruit_hotkey_frame.pack(fill='x', padx=10, pady=5)
        
        store_fruit_hotkey_label = ctk.CTkLabel(
            store_fruit_hotkey_frame,
            text="Anything else hotkey:",
            font=("Arial", 10),
            text_color="white"
        )
        store_fruit_hotkey_label.pack(side=tk.LEFT, padx=5)
        
        anything_else_hotkey_combobox = ctk.CTkComboBox(
            store_fruit_hotkey_frame,
            values=[str(i) for i in range(10)],
            variable=self.anything_else_hotkey_var,
            width=60,
            font=("Arial", 10)
        )
        anything_else_hotkey_combobox.pack(side=tk.LEFT, padx=5)
        
        # Pack content frame based on checkbox state
        if self.auto_store_devil_fruit_var.get():
            self.auto_store_content_frame.pack(fill='x', padx=10, pady=10)
        
        # Add some bottom padding
        ctk.CTkLabel(scrollable_frame, text="", font=("Arial", 10), text_color="gray").pack(pady=20)
    
    def toggle_auto_buy_section(self):
        """Show/hide the Auto Buy Common Bait section based on checkbox state"""
        if self.auto_buy_common_bait_var.get():
            self.auto_buy_content_frame.pack(fill='x', padx=10, pady=10)
        else:
            self.auto_buy_content_frame.pack_forget()
        self.save_settings()
    
    def toggle_auto_store_section(self):
        """Show/hide the Auto Store Devil Fruit section based on checkbox state"""
        if self.auto_store_devil_fruit_var.get():
            self.auto_store_content_frame.pack(fill='x', padx=10, pady=10)
        else:
            self.auto_store_content_frame.pack_forget()
        self.save_settings()

    def update_waiting_timeout(self):
        """Update waiting_timeout from the spinbox value"""
        try:
            new_value = int(self.waiting_timeout_var.get())
            if 5 <= new_value <= 60:
                self.waiting_timeout = new_value
                print(f"[DEBUG] Waiting timeout updated to: {self.waiting_timeout} seconds")
                self.save_settings()
        except (ValueError, tk.TclError):
            # Invalid input, reset to current value
            self.waiting_timeout_var.set(self.waiting_timeout)

    def build_postcast_tab(self, parent):
        """Build the Post-cast tab with timeout and recast settings"""
        scrollable_frame = ctk.CTkScrollableFrame(
            parent, 
            label_text="Post-cast Controls",
            fg_color="#2b2b2b"
        )
        scrollable_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Waiting Timeout section
        timeout_frame = ctk.CTkFrame(
            scrollable_frame,
            fg_color="#333333"
        )
        timeout_frame.pack(fill='x', padx=20, pady=10)
        
        # Section title
        ctk.CTkLabel(
            timeout_frame,
            text="Waiting Timeout",
            font=("Arial", 12, "bold"),
            text_color="white"
        ).pack(pady=(10, 5))
        
        # Description
        ctk.CTkLabel(
            timeout_frame,
            text="Max seconds to wait bite before recasting",
            font=("Arial", 10),
            text_color="lightgray"
        ).pack(pady=(0, 10))
        
        # Timeout spinbox with label
        timeout_inner_frame = ctk.CTkFrame(timeout_frame, fg_color="#333333")
        timeout_inner_frame.pack(pady=5)
        
        timeout_label = ctk.CTkLabel(
            timeout_inner_frame,
            text="Timeout (seconds):",
            font=("Arial", 10),
            text_color="white"
        )
        timeout_label.pack(side=tk.LEFT, padx=5)
        
        self.waiting_timeout_var = tk.IntVar(value=self.waiting_timeout)
        timeout_spinbox = tk.Spinbox(
            timeout_inner_frame,
            from_=5,
            to=60,
            textvariable=self.waiting_timeout_var,
            width=10,
            font=("Arial", 10),
            increment=5,
            command=self.update_waiting_timeout
        )
        timeout_spinbox.pack(side=tk.LEFT, padx=5)
        
        # Also update when value changes via arrow keys
        timeout_spinbox.bind('<KeyRelease>', lambda e: self.root.after(100, self.update_waiting_timeout))
        timeout_spinbox.bind('<ButtonRelease-1>', lambda e: self.root.after(100, self.update_waiting_timeout))
        
        # Add some bottom padding
        ctk.CTkLabel(scrollable_frame, text="", font=("Arial", 10), text_color="gray").pack(pady=20)

    # Button handler
    def handle_button_press(self, action):
        print(f"Button pressed: {action}")
        if action == "start_stop":
            self.start_stop()
        elif action == "toggle_area":
            self.toggle_area()
    
    # Water point setting
    def set_water_point(self):
        if self.start_stop_state:
            print("Cannot set water point while macro is running!")
            return
        
        self.setting_water_point = True
        self.water_point_button.configure(fg_color="#FFD700", text="Click on water...")
        print("Click anywhere on screen to set water point...")
        
        # Start mouse listener for water point
        if self.mouse_listener:
            self.mouse_listener.stop()
        self.mouse_listener = mouse.Listener(on_click=self.on_water_point_click)
        self.mouse_listener.start()
    
    def on_water_point_click(self, x, y, button, pressed):
        if self.setting_water_point and pressed:
            self.water_point = (x, y)
            self.settings["water_point"] = self.water_point
            self.save_settings()
            print(f"Water point set to: {self.water_point}")
            
            # Update UI
            self.water_point_label.configure(text=f"Current: {self.water_point}")
            self.water_point_button.configure(fg_color="transparent", text="Set Water Point")
            
            # Stop listener
            self.setting_water_point = False
            if self.mouse_listener:
                self.mouse_listener.stop()
                self.mouse_listener = None
            return False  # Stop listening

    # Auto Buy Common Bait Point Setting Methods
    def set_left_point(self):
        """Start setting left point for auto buy"""
        if self.start_stop_state:
            print("Cannot set left point while macro is running!")
            return
        
        self.setting_left_point = True
        self.left_point_button.configure(fg_color="#FFD700", text="Click on Left Point...")
        print("Click anywhere on screen to set left point...")
        
        # Start mouse listener
        if self.mouse_listener:
            self.mouse_listener.stop()
        self.mouse_listener = mouse.Listener(on_click=self.on_bait_point_click)
        self.mouse_listener.start()
    
    def set_middle_point(self):
        """Start setting middle point for auto buy"""
        if self.start_stop_state:
            print("Cannot set middle point while macro is running!")
            return
        
        self.setting_middle_point = True
        self.middle_point_button.configure(fg_color="#FFD700", text="Click on Middle Point...")
        print("Click anywhere on screen to set middle point...")
        
        # Start mouse listener
        if self.mouse_listener:
            self.mouse_listener.stop()
        self.mouse_listener = mouse.Listener(on_click=self.on_bait_point_click)
        self.mouse_listener.start()
    
    def set_right_point(self):
        """Start setting right point for auto buy"""
        if self.start_stop_state:
            print("Cannot set right point while macro is running!")
            return
        
        self.setting_right_point = True
        self.right_point_button.configure(fg_color="#FFD700", text="Click on Right Point...")
        print("Click anywhere on screen to set right point...")
        
        # Start mouse listener
        if self.mouse_listener:
            self.mouse_listener.stop()
        self.mouse_listener = mouse.Listener(on_click=self.on_bait_point_click)
        self.mouse_listener.start()
    
    def on_bait_point_click(self, x, y, button, pressed):
        """Handle clicks for setting bait points"""
        if pressed:
            # Check which point is being set
            if self.setting_left_point:
                self.left_point = (x, y)
                self.settings["left_point"] = self.left_point
                self.save_settings()
                print(f"Left point set to: {self.left_point}")
                
                # Update UI
                self.left_point_label.configure(text=f"Current: {self.left_point}")
                self.left_point_button.configure(fg_color="transparent", text="Set Left Point")
                
                # Stop listener
                self.setting_left_point = False
                if self.mouse_listener:
                    self.mouse_listener.stop()
                    self.mouse_listener = None
                return False
            
            elif self.setting_middle_point:
                self.middle_point = (x, y)
                self.settings["middle_point"] = self.middle_point
                self.save_settings()
                print(f"Middle point set to: {self.middle_point}")
                
                # Update UI
                self.middle_point_label.configure(text=f"Current: {self.middle_point}")
                self.middle_point_button.configure(fg_color="transparent", text="Set Middle Point")
                
                # Stop listener
                self.setting_middle_point = False
                if self.mouse_listener:
                    self.mouse_listener.stop()
                    self.mouse_listener = None
                return False
            
            elif self.setting_right_point:
                self.right_point = (x, y)
                self.settings["right_point"] = self.right_point
                self.save_settings()
                print(f"Right point set to: {self.right_point}")
                
                # Update UI
                self.right_point_label.configure(text=f"Current: {self.right_point}")
                self.right_point_button.configure(fg_color="transparent", text="Set Right Point")
                
                # Stop listener
                self.setting_right_point = False
                if self.mouse_listener:
                    self.mouse_listener.stop()
                    self.mouse_listener = None
                return False
    
    # Store Fruit Point Setting Methods
    def set_store_fruit_point(self):
        """Start setting store fruit point for auto store devil fruit"""
        if self.start_stop_state:
            return
        
        self.setting_store_fruit_point = True
        self.store_fruit_point_button.configure(fg_color="#FFD700", text="Click on Store Fruit Point...")
        
        # Start mouse listener
        if self.mouse_listener:
            self.mouse_listener.stop()
        self.mouse_listener = mouse.Listener(on_click=self.on_store_fruit_point_click)
        self.mouse_listener.start()
    
    def on_store_fruit_point_click(self, x, y, button, pressed):
        """Handle clicks for setting store fruit point"""
        if self.setting_store_fruit_point and pressed:
            self.store_fruit_point = (x, y)
            self.settings["store_fruit_point"] = self.store_fruit_point
            self.save_settings()
            
            # Update UI
            self.store_fruit_point_label.configure(text=f"Point: {self.store_fruit_point}")
            self.store_fruit_point_button.configure(fg_color="transparent", text="Set Store Fruit Point")
            
            # Stop listener
            self.setting_store_fruit_point = False
            if self.mouse_listener:
                self.mouse_listener.stop()
                self.mouse_listener = None
            return False  # Stop listening
    
    def set_store_df_area(self):
        """Start setting store DF area for auto store devil fruit"""
        if self.start_stop_state:
            return
        
        self.setting_store_df_area = True
        self.store_df_area_button.configure(fg_color="#FFD700", text="Select Area...")
        
        # Use OverlaySelector for rectangular area selection
        if self.store_df_area_selector:
            self.store_df_area_selector.close()
        
        self.store_df_area_selector = OverlaySelector(
            self.root, 
            self.store_df_area, 
            None,  # No drop area needed for store DF
            self.on_store_df_area_selected
        )
    
    def on_store_df_area_selected(self, bar_coords, drop_coords):
        """Callback when OverlaySelector is closed with selected coordinates"""
        if bar_coords:
            self.store_df_area = bar_coords
            self.settings["store_df_area"] = self.store_df_area
            self.save_settings()
            
            # Update UI
            self.store_df_area_label.configure(text=f"Area: {self.store_df_area}")
            self.store_df_area_button.configure(fg_color="transparent", text="Set Store DF Area")
        
        self.store_df_area_selector = None
        self.setting_store_df_area = False

    def capture_drop_area(self):
        """Capture screenshot from the drop layout area
        
        Returns:
            numpy array of drop area screenshot or None if failed
        """
        try:
            if not self.drop_area:
                print("[FRUIT DETECTION] Drop area not configured")
                return None
            
            # Get drop area coordinates
            coords = self.drop_area
            x_min = int(min(coords["x1"], coords["x2"]))
            y_min = int(min(coords["y1"], coords["y2"]))
            x_max = int(max(coords["x1"], coords["x2"]))
            y_max = int(max(coords["y1"], coords["y2"]))
            
            monitor = {
                'left': x_min,
                'top': y_min,
                'width': x_max - x_min,
                'height': y_max - y_min
            }
            
            screenshot = self.sct.grab(monitor)
            img_array = np.array(screenshot)
            
            # Convert RGBA to RGB if needed
            if len(img_array.shape) == 3 and img_array.shape[2] == 4:
                img_array = img_array[:, :, :3]
            
            print(f"[FRUIT DETECTION] Captured drop area: {monitor['width']}x{monitor['height']}")
            return img_array
            
        except Exception as e:
            print(f"[FRUIT DETECTION] Failed to capture drop area: {e}")
            return None

    def detect_devil_fruit_in_drop(self):
        """Detect devil fruit drop message using Tesseract OCR.
        
        Detects:
        - "All Seeing Eye: YOU GOT A DEVIL FRUIT DROP, CHECK YOUR BACKPACK!"
        - "Legendary pity"
        
        Returns:
            True if devil fruit message detected, False otherwise
        """
        current_time = time.time()
        
        # Check cooldown to prevent spam
        if current_time - self.last_fruit_check_time < self.fruit_check_cooldown:
            return self.devil_fruit_detected
        
        self.last_fruit_check_time = current_time
        
        # Capture drop area
        screenshot = self.capture_drop_area()
        if screenshot is None:
            return False
        
        if not TESSERACT_AVAILABLE:
            print("[FRUIT DETECTION] PyTesseract not available!")
            print("[FRUIT DETECTION] Install with: pip install pytesseract")
            print("[FRUIT DETECTION] Also install Tesseract: brew install tesseract")
            return False
        
        # Convert to PIL Image for Tesseract
        pil_image = Image.fromarray(screenshot)
        
        # Save screenshot for debugging (replaces previous screenshot)
        try:
            screenshot_dir = "fishing_screenshots"
            if not os.path.exists(screenshot_dir):
                os.makedirs(screenshot_dir, exist_ok=True)
            screenshot_path = os.path.join(screenshot_dir, "fruit_ocr_debug.png")
            pil_image_debug = Image.fromarray(screenshot)
            pil_image_debug.save(screenshot_path)
            print(f"[FRUIT DETECTION] Saved debug screenshot to: {screenshot_path}")
        except Exception as save_error:
            print(f"[FRUIT DETECTION] Failed to save screenshot: {save_error}")
        
        # Preprocess image for better OCR
        try:
            # Convert to grayscale
            gray_image = pil_image.convert('L')
            
            # Increase contrast using point operation
            enhanced_image = gray_image.point(lambda x: 0 if x < 128 else 255)
            
            print("[FRUIT DETECTION] Running Tesseract OCR...")
            detected_text = pytesseract.image_to_string(enhanced_image).lower()
            print(f"[FRUIT DETECTION] Tesseract detected: {detected_text}")
        except Exception as e:
            print(f"[FRUIT DETECTION] Tesseract error: {e}")
            return False
        
        # Check for devil fruit messages
        message1 = "all seeing eye: you got a devil fruit drop, check your backpack"
        message2 = "legendary pity"
        
        # Count matching words
        message1_words = set(message1.split())
        message2_words = set(message2.split())
        detected_words = set(detected_text.split())
        
        message1_matches = len(message1_words & detected_words)
        message2_matches = len(message2_words & detected_words)
        
        print(f"[FRUIT DETECTION] Message 1: {message1_matches}/{len(message1_words)} words")
        print(f"[FRUIT DETECTION] Message 2: {message2_matches}/{len(message2_words)} words")
        
        # Require at least 2 matching words (or all words for short messages)
        message1_threshold = max(2, int(len(message1_words) * 0.2))  # 20% or 2 words, whichever is higher
        message2_threshold = max(2, int(len(message2_words) * 0.5))  # 50% or 2 words, whichever is higher
        
        if message1_matches >= message1_threshold:
            print(f"[FRUIT DETECTION] Devil fruit detected! (Message 1)")
            self.devil_fruit_detected = True
        elif message2_matches >= message2_threshold:
            print(f"[FRUIT DETECTION] Devil fruit detected! (Message 2)")
            self.devil_fruit_detected = True
        else:
            print(f"[FRUIT DETECTION] No devil fruit message detected")
            self.devil_fruit_detected = False
        
        return self.devil_fruit_detected
    
    def check_and_store_devil_fruit(self):
        """Check for devil fruit in drop area and store if detected
        
        Returns:
            True if store sequence was executed, False if skipped
        """
        print("[DEBUG] check_and_store_devil_fruit() called")
        print(f"[DEBUG] drop_area configured: {self.drop_area is not None}")
        print(f"[DEBUG] auto_store_devil_fruit enabled: {self.auto_store_devil_fruit_var.get()}")
        
        # EXIT EARLY if auto store is disabled - don't run any OCR or detection code
        if not self.auto_store_devil_fruit_var.get():
            print("[DEBUG] check_and_store_devil_fruit(): Auto store devil fruit is DISABLED, skipping")
            return False
        
        # Check if fruit detection area is set
        if not self.drop_area:
            print("[DEBUG] check_and_store_devil_fruit(): No drop area configured, skipping")
            return False
        
        # Check for devil fruit in drop area
        print("[DEBUG] check_and_store_devil_fruit(): Calling detect_devil_fruit_in_drop()")
        fruit_detected = self.detect_devil_fruit_in_drop()
        print(f"[DEBUG] check_and_store_devil_fruit(): fruit_detected={fruit_detected}")
        
        if fruit_detected:
            print("[DEBUG] check_and_store_devil_fruit(): Devil fruit detected! Calling run_auto_store_devil_fruit()")
            self.run_auto_store_devil_fruit()
            print("[DEBUG] check_and_store_devil_fruit(): run_auto_store_devil_fruit() returned")
            return True
        else:
            print("[DEBUG] check_and_store_devil_fruit(): No devil fruit detected, skipping store sequence")
            return False

    def run_auto_buy_common_bait(self):
        """Run the auto-buy common bait sequence at shop"""
        if not self.auto_buy_common_bait_var.get():
            return
        
        # Check if all required points are set
        if not self.left_point or not self.middle_point or not self.right_point:
            return
        
        # Get loops per purchase value
        loops_value = self.loops_per_purchase_var.get()
        
        try:
            # Step 1: Click to focus window (only if not already focused)
            from pynput.keyboard import Key
            self.keyboard = pkb.Controller()
            
            # Check if Roblox is already the frontmost/active window
            window_focused = False
            try:
                from AppKit import NSWorkspace
                active_app = NSWorkspace.sharedWorkspace().activeApplication()
                if active_app and 'oblox' in active_app['NSApplicationName'].lower():
                    window_focused = True
            except:
                pass
            
            if not window_focused:
                # Click to focus the window
                self.mouse_controller.click(Button.left, 1)
                time.sleep(0.1)
            
            # Press E to interact with shop
            self.keyboard.press('e')
            self.keyboard.release('e')
            # Use interruptible sleep - check if we should stop
            if self.interruptible_sleep(1):
                return
            
            # Step 3: Click left point
            self.mouse_controller.position = self.left_point
            time.sleep(0.3)
            self.mouse_controller.click(Button.left, 1)
            # Use interruptible sleep
            if self.interruptible_sleep(1):
                return
            
            # Step 4: Click middle point
            self.mouse_controller.position = self.middle_point
            time.sleep(0.3)
            self.mouse_controller.click(Button.left, 1)
            # Use interruptible sleep
            if self.interruptible_sleep(1):
                return
            
            # Step 5: Type loops per purchase value
            # Use slow individual key presses to ensure Roblox captures all characters
            typed_value = str(self.loops_per_purchase_var.get())
            for char in typed_value:
                if self.stop_requested:
                    return
                self.keyboard.press(char)
                self.keyboard.release(char)
                time.sleep(0.05)  # 50ms delay between each character
            # Use interruptible sleep
            if self.interruptible_sleep(1):
                return
            
            # Step 6: Click left point
            self.mouse_controller.position = self.left_point
            time.sleep(0.3)
            self.mouse_controller.click(Button.left, 1)
            # Use interruptible sleep
            if self.interruptible_sleep(1):
                return
            
            # Step 7: Click right point
            self.mouse_controller.position = self.right_point
            time.sleep(0.3)
            self.mouse_controller.click(Button, 1)
            # Use interruptible sleep
            if self.interruptible_sleep(1):
                return
            
            # Step 8: Click middle point
            self.mouse_controller.position = self.middle_point
            time.sleep(0.3)
            self.mouse_controller.click(Button.left, 1)
            # Use interruptible sleep
            if self.interruptible_sleep(1):
                return
            
        except Exception as e:
            pass

    def run_auto_store_devil_fruit(self):
        """Run the store devil fruit sequence after a catch"""
        print("[DEBUG] run_auto_store_devil_fruit() called")
        
        if not self.auto_store_devil_fruit_var.get():
            print("[DEBUG] run_auto_store_devil_fruit(): Auto store devil fruit is DISABLED (checkbox not checked)")
            return
        
        print("[DEBUG] run_auto_store_devil_fruit(): Auto store devil fruit is ENABLED")
        
        if not self.store_df_area and not self.store_fruit_point:
            print("[DEBUG] run_auto_store_devil_fruit(): store_df_area and store_fruit_point are NOT SET, returning")
            return
        
        print(f"[DEBUG] run_auto_store_devil_fruit(): store_fruit_point is set to: {self.store_fruit_point}")
        print(f"[DEBUG] run_auto_store_devil_fruit(): store_df_area is set to: {self.store_df_area}")
        print(f"[DEBUG] run_auto_store_devil_fruit(): Devil fruit hotkey: {self.devil_fruit_hotkey_var.get()}")
        print(f"[DEBUG] run_auto_store_devil_fruit(): Rod hotkey: {self.rod_hotkey_var.get()}")
        
        try:
            # First, ensure Roblox window is focused and active using pyobjc
            roblox_app = None
            try:
                apps = NSWorkspace.sharedWorkspace().runningApplications()
                for app in apps:
                    if 'oblox' in app.localizedName().lower():
                        roblox_app = app
                        break
                
                if roblox_app:
                    # Activate the app (brings all windows to front, makes active)
                    roblox_app.activateWithOptions_(1)  # 1 = NSApplicationActivateAllWindows
                    print("[DEBUG] run_auto_store_devil_fruit(): Activated Roblox application")
                else:
                    print("[DEBUG] run_auto_store_devil_fruit(): Roblox app not found")
            except Exception as e:
                print(f"[DEBUG] run_auto_store_devil_fruit(): Could not activate Roblox: {e}")
            
            # Give window time to fully activate
            time.sleep(0.5)
            print("[DEBUG] run_auto_store_devil_fruit(): Done waiting for window activation")
            
            # 0. Deselect rod by pressing rod hotkey first (in case rod was selected from fishing)
            print("[DEBUG] run_auto_store_devil_fruit(): Deselecting rod first...")
            rod_key = str(self.rod_hotkey_var.get())
            rod_code = KEY_CODES.get(rod_key)
            if rod_code:
                print(f"[DEBUG] run_auto_store_devil_fruit(): Pressing rod key: {rod_key} (code: {hex(rod_code)}) to deselect")
                press_key(rod_code)
                release_key(rod_code)
            else:
                print(f"[DEBUG] run_auto_store_devil_fruit(): Unknown key code for: {rod_key}")
            
            # Wait a bit after deselecting rod
            print("[DEBUG] run_auto_store_devil_fruit(): Waiting 0.3s after rod deselect...")
            if self.interruptible_sleep(0.3):
                print("[DEBUG] run_auto_store_devil_fruit(): Interrupted during rod deselect, returning")
                return
            
            # 1. Press devil fruit hotkey using CGEvent
            devil_key = str(self.devil_fruit_hotkey_var.get())
            devil_code = KEY_CODES.get(devil_key)
            if devil_code:
                print(f"[DEBUG] run_auto_store_devil_fruit(): Pressing devil fruit key: {devil_key} (code: {hex(devil_code)})")
                press_key(devil_code)
                release_key(devil_code)
            else:
                print(f"[DEBUG] run_auto_store_devil_fruit(): Unknown key code for: {devil_key}")
            
            # Wait 1 second
            print("[DEBUG] run_auto_store_devil_fruit(): Waiting 1 second...")
            if self.interruptible_sleep(1):
                print("[DEBUG] run_auto_store_devil_fruit(): Interrupted during step 1, returning")
                return
            
            # 3. Click on store_fruit_point (NOT store_df_area - store_df_area is only for fruit detection)
            if self.store_fruit_point:
                click_point = self.store_fruit_point
                print(f"[DEBUG] run_auto_store_devil_fruit(): Clicking on store_fruit_point: {click_point}")
            else:
                print(f"[DEBUG] run_auto_store_devil_fruit(): store_fruit_point not set, returning")
                return
            
            print(f"[DEBUG] run_auto_store_devil_fruit(): Moving mouse to {click_point}")
            self.mouse_controller.position = click_point
            time.sleep(0.3)
            print("[DEBUG] run_auto_store_devil_fruit(): Clicking...")
            self.mouse_controller.click(Button.left, 1)
            
            # Wait 2 seconds
            print("[DEBUG] run_auto_store_devil_fruit(): Waiting 2 seconds...")
            if self.interruptible_sleep(2):
                print("[DEBUG] run_auto_store_devil_fruit(): Interrupted during step 2, returning")
                return
            
            # 4. Press Shift using CGEvent
            print("[DEBUG] run_auto_store_devil_fruit(): Pressing Shift...")
            press_key(KEY_CODES['shift'])
            release_key(KEY_CODES['shift'])
            
            # Wait 500ms
            print("[DEBUG] run_auto_store_devil_fruit(): Waiting 500ms...")
            if self.interruptible_sleep(0.5):
                print("[DEBUG] run_auto_store_devil_fruit(): Interrupted during step 3, returning")
                return
            
            # 5. Press Backspace using CGEvent
            print("[DEBUG] run_auto_store_devil_fruit(): Pressing Backspace...")
            press_key(KEY_CODES['backspace'])
            release_key(KEY_CODES['backspace'])
            
            # Wait 1.5 seconds
            print("[DEBUG] run_auto_store_devil_fruit(): Waiting 1.5 seconds...")
            if self.interruptible_sleep(1.5):
                print("[DEBUG] run_auto_store_devil_fruit(): Interrupted during step 4, returning")
                return
            
            # 9. Press Shift using CGEvent
            print("[DEBUG] run_auto_store_devil_fruit(): Pressing Shift...")
            press_key(KEY_CODES['shift'])
            release_key(KEY_CODES['shift'])
            
            # 10. Press rod hotkey using CGEvent
            rod_key = str(self.rod_hotkey_var.get())
            rod_code = KEY_CODES.get(rod_key)
            if rod_code:
                print(f"[DEBUG] run_auto_store_devil_fruit(): Pressing rod key: {rod_key} (code: {hex(rod_code)})")
                press_key(rod_code)
                release_key(rod_code)
            else:
                print(f"[DEBUG] run_auto_store_devil_fruit(): Unknown key code for: {rod_key}")
            
            print("[DEBUG] run_auto_store_devil_fruit() completed successfully!")
            
        except Exception as e:
            print(f"Error in run_auto_store_devil_fruit: {e}")
            import traceback
            traceback.print_exc()

    # Hotkeys
    def on_hotkey_press(self, key):
        key_name = None
        key_char = None
        
        try:
            if hasattr(key, "char") and key.char is not None:
                key_char = key.char.lower()
            if hasattr(key, "name") and key.name is not None:
                key_name = key.name.lower()
        except Exception as e:
            return
        
        # Create a mapping of key names to their character equivalents
        key_map = {
            "bracketleft": "[",
            "bracketright": "]",
        }
        
        for action, hotkey in self.hotkeys.items():
            hotkey_lower = hotkey.lower()
            # Check if either the key name matches, or the character matches, or the mapped character matches
            if (key_name and key_name == hotkey_lower) or \
               (key_char and key_char == hotkey_lower) or \
               (key_char and key_char == key_map.get(hotkey_lower)):
                if action == "exit":
                    # Exit immediately without cleanup - force kill
                    self.stop_requested = True
                    self.main_loop_running = False
                    os._exit(0)
                else:
                    # Set stop_requested immediately for instant response
                    if action == "start_stop":
                        self.stop_requested = True
                    # Use lambda with default argument to capture action correctly
                    self.root.after(0, lambda act=action: self.handle_button_press(act))
                break

    def change_hotkey(self, action):
        original_text = self.buttons[action].cget("text")
        self.buttons[action].configure(text="Press any key...")
        
        def on_key_press(event):
            new_hotkey = event.keysym.lower()
            self.hotkeys[action] = new_hotkey
            display_key = DISPLAY_KEYS.get(new_hotkey, new_hotkey.upper())
            
            if action == "start_stop":
                label = "Start/Stop"
            elif action == "toggle_area":
                label = "Change Area"
            elif action == "exit":
                label = "Exit"
            else:
                label = action.replace('_', ' ').title()
                
            self.buttons[action].configure(text=f"{label} ({display_key})")
            self.root.unbind("<KeyPress>")
            print(f"Hotkey for {action} changed to: {new_hotkey}")

        self.root.bind("<KeyPress>", on_key_press)

    # DEBUG FUNCTIONS
    def create_debug_overlay(self):
        """Just use terminal output - Quartz causes crashes"""
        print("Debug mode active - coordinates will be printed to terminal")
    
    def destroy_debug_overlay(self):
        """Cleanup"""
        pass
    
    def draw_debug_arrow(self, x):
        """Just track the position"""
        pass
    
    def clear_debug_arrow(self):
        """Just track the position"""
        pass
    
    def draw_dark_arrows(self, x, top_y, bottom_y):
        """Just track the positions"""
        pass
    
    def clear_dark_arrows(self):
        """Just track the positions"""
        pass

    # Main loop
    def start_stop(self):
        print("[DEBUG] start_stop() called")
        
        if self.toggle_area_state:
            print("[DEBUG] toggle_area_state is True, returning early")
            return
        
        # CRITICAL: Reset stop_requested at the VERY START to prevent stale flags
        if not self.start_stop_state:
            print("[DEBUG] Starting macro - resetting stop_requested = False")
            self.stop_requested = False
            
        self.start_stop_state = not self.start_stop_state
        print(f"[DEBUG] start_stop_state changed to: {self.start_stop_state}")
        
        self.main_loop_running = self.start_stop_state
        if self.start_stop_state:
            self.buttons["start_stop"].configure(
                fg_color="#32CD32",
                hover_color="#228B22"
            )
        else:
            # Reset to default CTk blue button color
            self.buttons["start_stop"].configure(
                fg_color="#3B8ED0",
                hover_color="#3B7ED0"
            )
        self.update_status()
        # Force UI refresh so status shows immediately
        self.root.update()
        
        if self.start_stop_state:
            print("[DEBUG] Starting fishing macro...")
            # Reset stop_requested flag
            self.stop_requested = False
            # Reset PID controller state
            self.previous_error = 0
            self.integral = 0
            self.previous_time = None
            # Reset fishing state
            self.fishing_state = "IDLE"
            self.cast_time = None
            self.blue_lost_time = None
            self.recast_locked = False
            self.waiting_start_time = None
            # Reset loop counter
            self.fishing_loop_count = 0
            if self.debug_mode:
                self.create_debug_overlay()
            # Run auto-buy at start if enabled
            self.run_auto_buy_common_bait()
            print("[DEBUG] Starting main_loop thread...")
            threading.Thread(target=self.main_loop, daemon=True).start()
            print("[DEBUG] main_loop thread started")
        else:
            # Request immediate stop
            print("[DEBUG] Stopping macro - setting stop_requested = True")
            self.stop_requested = True
            # Release click when stopping
            if self.is_holding_click:
                self.mouse_controller.release(Button.left)
                self.is_holding_click = False
            if self.debug_mode:
                self.destroy_debug_overlay()

    def main_loop(self):
        print("[DEBUG] main_loop() thread started")
        loop_count = 0
        
        while self.main_loop_running:
            try:
                if self.fishing_state == "IDLE" or self.fishing_state == "CASTING":
                    self.cast()
                elif self.fishing_state == "WAITING":
                    self.waiting()
                elif self.fishing_state == "FISHING":
                    self.fishing()
                else:
                    print(f"[DEBUG] main_loop: Unknown fishing_state: {self.fishing_state}, resetting to IDLE")
                    # Reset to IDLE to recover from unknown state
                    self.fishing_state = "IDLE"
                
                loop_count += 1
                if loop_count % 1000 == 0:
                    print(f"[DEBUG] main_loop running, fishing_state={self.fishing_state}, loop_count={loop_count}")
                
                time.sleep(0.001)
            except Exception as e:
                print(f"[ERROR] main_loop exception: {e}")
                import traceback
                traceback.print_exc()
                break
        
        print(f"[DEBUG] main_loop() thread exited, main_loop_running={self.main_loop_running}")

    # Fishing stages
    def cast(self):
        if self.fishing_state == "IDLE":
            # Double click - first to focus window, second to cast
            time.sleep(0.1)  # Short delay before casting
            
            # Move to water point if set, otherwise use current position
            if self.water_point:
                self.mouse_controller.position = self.water_point
            current_pos = self.mouse_controller.position
            self.mouse_controller.click(Button.left, 2)  # Double click
            self.fishing_state = "CASTING"
            self.cast_time = time.time()
        elif self.fishing_state == "CASTING":
            # Wait a moment after casting before checking for blue
            time_since_cast = time.time() - self.cast_time
            if time_since_cast > 1.0:  # Wait 1 second after cast
                self.fishing_state = "WAITING"
                self.waiting_start_time = time.time()  # Mark when we started waiting
    
    def waiting(self):
        # Wait at least 0.3 seconds before checking for blue (to let screen settle after cast)
        if self.waiting_start_time is not None:
            time_waiting = time.time() - self.waiting_start_time
            if time_waiting < 0.3:
                return  # Don't check yet, screen might still have residual blue
        else:
            self.waiting_start_time = time.time()
            return
        
        # Check if blue color appears
        blue_detected = self.check_for_blue()
        
        if blue_detected:
            self.fishing_state = "FISHING"
            self.blue_lost_time = None
            self.waiting_start_time = None
        else:
            # Check if we've been waiting too long (configurable timeout)
            if self.waiting_start_time is not None:
                time_in_waiting = time.time() - self.waiting_start_time
                if time_in_waiting > self.waiting_timeout:
                    print(f"[DEBUG] waiting(): Timeout ({self.waiting_timeout}s), switching back to IDLE to recast")
                    self.fishing_state = "IDLE"
                    self.cast_time = None
                    self.waiting_start_time = None
    
    def check_for_blue(self):
        """Check if the blue color exists on screen"""
        try:
            target_color = (107, 168, 248)
            tolerance = 2
            
            if self.bar_area:
                coords = self.bar_area
                x_min, x_max = int(min(coords["x1"], coords["x2"])), int(max(coords["x1"], coords["x2"]))
                y_min, y_max = int(min(coords["y1"], coords["y2"])), int(max(coords["y1"], coords["y2"]))
                
                monitor = {
                    "left": x_min,
                    "top": y_min,
                    "width": x_max - x_min,
                    "height": y_max - y_min
                }
            else:
                monitor = self.sct.monitors[1]
            
            screenshot = self.sct.grab(monitor)
            img_array = np.array(screenshot)[:, :, :3]
            img_array = img_array[:, :, ::-1]
            
            r_diff = np.abs(img_array[:, :, 0].astype(int) - target_color[0])
            g_diff = np.abs(img_array[:, :, 1].astype(int) - target_color[1])
            b_diff = np.abs(img_array[:, :, 2].astype(int) - target_color[2])
            
            color_mask = (r_diff <= tolerance) & (g_diff <= tolerance) & (b_diff <= tolerance)
            
            return np.any(color_mask)
        except Exception as e:
            print(f"Error checking for blue: {e}")
            return False
    
    def check_for_black_screen(self):
        """Check if half of the MSS image is RGB(0, 0, 0) - anti-macro detection"""
        try:
            # Target color: pure black
            target_color = (0, 0, 0)
            tolerance = 0  # Exact match for pure black
            
            if self.bar_area:
                coords = self.bar_area
                x_min, x_max = int(min(coords["x1"], coords["x2"])), int(max(coords["x1"], coords["x2"]))
                y_min, y_max = int(min(coords["y1"], coords["y2"])), int(max(coords["y1"], coords["y2"]))
                
                monitor = {
                    "left": x_min,
                    "top": y_min,
                    "width": x_max - x_min,
                    "height": y_max - y_min
                }
            else:
                monitor = self.sct.monitors[1]
            
            screenshot = self.sct.grab(monitor)
            img_array = np.array(screenshot)[:, :, :3]
            img_array = img_array[:, :, ::-1]
            
            # Check for pure black pixels
            r_diff = np.abs(img_array[:, :, 0].astype(int) - target_color[0])
            g_diff = np.abs(img_array[:, :, 1].astype(int) - target_color[1])
            b_diff = np.abs(img_array[:, :, 2].astype(int) - target_color[2])
            
            black_mask = (r_diff <= tolerance) & (g_diff <= tolerance) & (b_diff <= tolerance)
            
            # Calculate percentage of black pixels
            total_pixels = img_array.shape[0] * img_array.shape[1]
            black_pixels = np.sum(black_mask)
            black_percentage = (black_pixels / total_pixels) * 100 if total_pixels > 0 else 0
            
            # Return True if at least 50% is black (anti-macro detected)
            return black_percentage >= 50, black_percentage
        except Exception as e:
            print(f"Error checking for black screen: {e}")
            return False, 0
    
    def spam_anything_else_hotkey(self):
        """Press the anything_else_hotkey using CGEvent"""
        try:
            anything_key = str(self.store_fruit_hotkey_var.get())
            anything_code = KEY_CODES.get(anything_key)
            if anything_code:
                press_key(anything_code)
                release_key(anything_code)
                return True
            else:
                print(f"[DEBUG] Unknown key code for anything_else_hotkey: {anything_key}")
                return False
        except Exception as e:
            print(f"Error pressing anything_else_hotkey: {e}")
            return False
    
    def fishing(self):
        try:
            # If we're locked into recasting, don't do any fishing logic
            if self.recast_locked:
                # Check if stop was requested IMMEDIATELY - exit early
                if self.stop_requested:
                    print("[DEBUG] fishing(): recast_locked but stop_requested=True, exiting")
                    # Reset all state
                    self.fishing_state = "IDLE"
                    self.blue_lost_time = None
                    self.recast_locked = False
                    # Release click if holding
                    if self.is_holding_click:
                        self.mouse_controller.release(Button.left)
                        self.is_holding_click = False
                    # Reset PID state
                    self.previous_error = 0
                    self.integral = 0
                    self.previous_time = None
                    return
                
                print(f"[DEBUG] fishing(): recast_locked=True, blue_lost_delay={self.blue_lost_delay}")
                elapsed = time.time() - self.blue_lost_time
                remaining = self.blue_lost_delay - elapsed
                
                # Check if we should still recast (in case of race condition)
                if not self.recast_locked:
                    print("[DEBUG] fishing(): recast_locked became False, returning")
                    return
                
                # If delay not reached yet, do the wait
                if remaining > 0:
                    print(f"[DEBUG] fishing(): recast_locked, waiting {remaining:.2f}s...")
                    if self.interruptible_sleep(remaining):
                        print("[DEBUG] fishing(): Sleep interrupted during recast_locked wait")
                    else:
                        print("[DEBUG] fishing(): Sleep completed normally")
                
                # Check stop_requested after sleep - exit if stopped
                if self.stop_requested:
                    print("[DEBUG] fishing(): Stop requested after delay wait, resetting state")
                    self.fishing_state = "IDLE"
                    self.blue_lost_time = None
                    self.recast_locked = False
                    if self.is_holding_click:
                        self.mouse_controller.release(Button.left)
                        self.is_holding_click = False
                    self.previous_error = 0
                    self.integral = 0
                    self.previous_time = None
                    return
                
                # Check again after sleep
                if not self.recast_locked:
                    print("[DEBUG] fishing(): recast_locked became False after sleep, returning")
                    return
                
                # Check if stop was requested after the sleep completes
                if self.stop_requested:
                    print("[DEBUG] fishing(): Stop requested after recast_locked delay, returning")
                    return
                
                print("[DEBUG] fishing(): Delay complete, checking for anti-macro black screen...")
                
                # Release click if holding
                if self.is_holding_click:
                    print("[DEBUG] fishing(): Releasing mouse click")
                    self.mouse_controller.release(Button.left)
                    self.is_holding_click = False
                
                # Check for anti-macro black screen (50% or more of image is RGB(0,0,0))
                is_black, black_percentage = self.check_for_black_screen()
                print(f"[DEBUG] fishing(): Black screen check: is_black={is_black}, black_percentage={black_percentage:.1f}%")
                
                if is_black:
                    # Anti-macro detected! Spam anything_else_hotkey until screen恢复正常
                    print("[DEBUG] fishing(): *** ANTI-MACRO BLACK SCREEN DETECTED! ***")
                    print("[DEBUG] fishing(): Spamming anything_else_hotkey every 250ms until screen恢复正常...")
                    
                    spam_count = 0
                    while True:
                        # Check if we should stop
                        if self.stop_requested or not self.recast_locked:
                            print(f"[DEBUG] fishing(): Stop requested or recast unlocked during anti-macro handling, returning")
                            return
                        
                        # Spam the anything_else_hotkey
                        self.spam_anything_else_hotkey()
                        spam_count += 1
                        
                        # Check if screen is still black
                        is_still_black, new_percentage = self.check_for_black_screen()
                        print(f"[DEBUG] fishing(): Anti-macro spam #{spam_count}, black_percentage={new_percentage:.1f}%")
                        
                        if not is_still_black:
                            # Screen恢复正常! Go back to start of main loop
                            print(f"[DEBUG] fishing(): Screen恢复正常 after {spam_count} spam attempts!")
                            print("[DEBUG] fishing(): Resetting to CASTING state (skipping store sequence)")
                            
                            # Reset to casting state - this goes back to main loop
                            # IMPORTANT: Do NOT reset cast_time! We want to keep the original
                            # cast time so the 1-second wait in CASTING state continues normally.
                            # This prevents the fast-casting issue.
                            self.fishing_state = "CASTING"
                            self.blue_lost_time = None
                            self.recast_locked = False
                            # Reset PID state
                            self.previous_error = 0
                            self.integral = 0
                            self.previous_time = None
                            return
                        
                        # Wait 250ms before next spam
                        if self.interruptible_sleep(0.25):
                            print("[DEBUG] fishing(): Sleep interrupted during anti-macro spam, returning")
                            return
                
                # Check if stop was requested before running store sequence
                if self.stop_requested:
                    print("[DEBUG] fishing(): Stop requested during recast_locked, resetting state")
                    # Reset all state and return
                    self.fishing_state = "IDLE"
                    self.blue_lost_time = None
                    self.recast_locked = False
                    # Release click if holding
                    if self.is_holding_click:
                        self.mouse_controller.release(Button.left)
                        self.is_holding_click = False
                    # Reset PID state
                    self.previous_error = 0
                    self.integral = 0
                    self.previous_time = None
                    return
                
                # Normal case: screen is not black, run store sequence
                print("[DEBUG] fishing(): No anti-macro detected, calling check_and_store_devil_fruit()...")
                
                # Check for devil fruit before running store sequence
                self.check_and_store_devil_fruit()
                
                print("[DEBUG] fishing(): check_and_store_devil_fruit() returned, resetting to IDLE")
                
                # Reset to casting state
                self.fishing_state = "IDLE"
                self.blue_lost_time = None
                self.recast_locked = False
                # Reset PID state
                self.previous_error = 0
                self.integral = 0
                self.previous_time = None
                return
            
            target_color = (107, 168, 248)
            tolerance = 9
            
            if self.bar_area:
                coords = self.bar_area
                x_min, x_max = int(min(coords["x1"], coords["x2"])), int(max(coords["x1"], coords["x2"]))
                y_min, y_max = int(min(coords["y1"], coords["y2"])), int(max(coords["y1"], coords["y2"]))
                
                monitor = {
                    "left": x_min,
                    "top": y_min,
                    "width": x_max - x_min,
                    "height": y_max - y_min
                }
                offset_x = x_min
            else:
                monitor = self.sct.monitors[1]
                offset_x = 0
            
            screenshot = self.sct.grab(monitor)
            img_array = np.array(screenshot)[:, :, :3]
            img_array = img_array[:, :, ::-1]
            
            r_diff = np.abs(img_array[:, :, 0].astype(int) - target_color[0])
            g_diff = np.abs(img_array[:, :, 1].astype(int) - target_color[1])
            b_diff = np.abs(img_array[:, :, 2].astype(int) - target_color[2])
            
            color_mask = (r_diff <= tolerance) & (g_diff <= tolerance) & (b_diff <= tolerance)
            
            if np.any(color_mask):
                y_coords, x_coords = np.where(color_mask)
                middle_x = int(np.median(x_coords)) + offset_x
                
                # Blue is present - reset timer ONLY if not already locked
                if not self.recast_locked:
                    self.blue_lost_time = None
                
                slice_x = int(np.median(x_coords))
                vertical_slice = img_array[:, slice_x:slice_x+1, :]
                
                dark_color = (25, 25, 25)
                dark_tolerance = 2
                
                r_diff_dark = np.abs(vertical_slice[:, 0, 0].astype(int) - dark_color[0])
                g_diff_dark = np.abs(vertical_slice[:, 0, 1].astype(int) - dark_color[1])
                b_diff_dark = np.abs(vertical_slice[:, 0, 2].astype(int) - dark_color[2])
                
                dark_mask = (r_diff_dark <= dark_tolerance) & (g_diff_dark <= dark_tolerance) & (b_diff_dark <= dark_tolerance)
                
                if self.debug_mode:
                    self.draw_debug_arrow(middle_x)
                    
                    if np.any(dark_mask):
                        dark_y_coords = np.where(dark_mask)[0]
                        top_y = int(dark_y_coords[0]) + (y_min if self.bar_area else 0)
                        bottom_y = int(dark_y_coords[-1]) + (y_min if self.bar_area else 0)
                        self.draw_dark_arrows(middle_x, top_y, bottom_y)
                        
                        # Second crop: 1 pixel wide, between top_y and bottom_y
                        local_top_y = int(dark_y_coords[0])
                        local_bottom_y = int(dark_y_coords[-1])
                        second_crop = vertical_slice[local_top_y:local_bottom_y+1, 0, :]
                        
                        # Search for white color in the second crop
                        white_color = (255, 255, 255)
                        white_tolerance = 2
                        
                        r_diff_white = np.abs(second_crop[:, 0].astype(int) - white_color[0])
                        g_diff_white = np.abs(second_crop[:, 1].astype(int) - white_color[1])
                        b_diff_white = np.abs(second_crop[:, 2].astype(int) - white_color[2])
                        
                        white_mask = (r_diff_white <= white_tolerance) & (g_diff_white <= white_tolerance) & (b_diff_white <= white_tolerance)
                        
                        white_height = 0
                        white_middle = None
                        
                        if np.any(white_mask):
                            white_y_coords = np.where(white_mask)[0]
                            white_top = int(white_y_coords[0])
                            white_bottom = int(white_y_coords[-1])
                            white_height = white_bottom - white_top + 1
                            white_middle = (white_top + white_bottom) // 2
                        
                        # Search for dark color in the second crop (user's controlled zone)
                        dark_color_2 = (25, 25, 25)
                        dark_tolerance_2 = 2
                        
                        r_diff_dark2 = np.abs(second_crop[:, 0].astype(int) - dark_color_2[0])
                        g_diff_dark2 = np.abs(second_crop[:, 1].astype(int) - dark_color_2[1])
                        b_diff_dark2 = np.abs(second_crop[:, 2].astype(int) - dark_color_2[2])
                        
                        dark_mask_2 = (r_diff_dark2 <= dark_tolerance_2) & (g_diff_dark2 <= dark_tolerance_2) & (b_diff_dark2 <= dark_tolerance_2)
                        
                        dark_middle = None
                        
                        if np.any(dark_mask_2):
                            dark_y_coords_2 = np.where(dark_mask_2)[0]
                            
                            # Group dark pixels with allowed gap of white_height * 2
                            max_gap = white_height * 2 if white_height > 0 else 0
                            
                            # Find groups
                            groups = []
                            current_group_start = dark_y_coords_2[0]
                            current_group_end = dark_y_coords_2[0]
                            
                            for i in range(1, len(dark_y_coords_2)):
                                gap = dark_y_coords_2[i] - current_group_end
                                
                                if gap <= max_gap + 1:
                                    current_group_end = dark_y_coords_2[i]
                                else:
                                    groups.append((current_group_start, current_group_end))
                                    current_group_start = dark_y_coords_2[i]
                                    current_group_end = dark_y_coords_2[i]
                            
                            groups.append((current_group_start, current_group_end))
                            
                            # Find biggest group by span
                            biggest_group = max(groups, key=lambda g: g[1] - g[0])
                            dark_middle = (biggest_group[0] + biggest_group[1]) // 2
                        
                        # PID CONTROLLER
                        if white_middle is not None and dark_middle is not None:
                            # Error: positive when white is ABOVE dark (smaller Y = higher on screen)
                            # Need to hold click to move dark up (reduce dark_middle)
                            error = dark_middle - white_middle
                            
                            # Get time delta
                            current_time = time.time()
                            if self.previous_time is None:
                                dt = 0.016  # ~60fps
                                self.previous_time = current_time
                            else:
                                dt = current_time - self.previous_time
                                self.previous_time = current_time
                            
                            # Prevent division by zero
                            if dt < 0.001:
                                dt = 0.001
                            
                            # Proportional term
                            p_term = self.kp * error
                            
                            # Integral term (accumulate error over time)
                            self.integral += error * dt
                            # Anti-windup: clamp integral
                            self.integral = max(self.integral_min, min(self.integral_max, self.integral))
                            i_term = self.ki * self.integral
                            
                            # Derivative term (rate of change of error)
                            derivative = (error - self.previous_error) / dt
                            d_term = self.kd * derivative
                            
                            # PID output
                            control_signal = p_term + i_term + d_term
                            
                            # Update previous error
                            self.previous_error = error
                            
                            # Binary control with hysteresis to prevent rapid switching
                            # Positive control signal = hold click (move dark up toward white)
                            # Negative control signal = release (let dark fall down)
                            if control_signal > self.switch_threshold:
                                if not self.is_holding_click:
                                    self.mouse_controller.press(Button.left)
                                    self.is_holding_click = True
                            elif control_signal < -self.switch_threshold:
                                if self.is_holding_click:
                                    self.mouse_controller.release(Button.left)
                                    self.is_holding_click = False
                    else:
                        self.clear_dark_arrows()
                        # If we can't find the dark bar, release click
                        if self.is_holding_click:
                            self.mouse_controller.release(Button.left)
                            self.is_holding_click = False
                else:
                    # If we can't find the dark bar, release click
                    if self.is_holding_click:
                        self.mouse_controller.release(Button.left)
                        self.is_holding_click = False
            else:
                if self.debug_mode:
                    self.clear_debug_arrow()
                    self.clear_dark_arrows()
                
                # Blue color disappeared - CATCH DETECTED!
                print("[DEBUG] fishing(): Blue color DISappeared - CATCH DETECTED!")
                if self.blue_lost_time is None:
                    # First time losing blue - start timer
                    print("[DEBUG] fishing(): Setting blue_lost_time (first time blue lost)")
                    self.blue_lost_time = time.time()
                    print(f"[DEBUG] fishing(): blue_lost_time = {self.blue_lost_time}")
                else:
                    # Check how long blue has been gone
                    elapsed = time.time() - self.blue_lost_time
                    print(f"[DEBUG] fishing(): blue_lost_time already set, elapsed={elapsed:.3f}s")
                    
                    # If blue has been gone for more than 0.1 seconds, lock into recast
                    if not self.recast_locked and elapsed > 0.1:
                        print("[DEBUG] fishing(): Locking recast_locked = True")
                        self.recast_locked = True
                    
                    if self.recast_locked:
                        print(f"[DEBUG] fishing(): Inside recast_locked block, elapsed={elapsed:.3f}s, blue_lost_delay={self.blue_lost_delay}s")
                        if elapsed >= self.blue_lost_delay:
                            print("[DEBUG] fishing(): *** DELAY REACHED - About to run post-catch sequence ***")
                            # Release click if holding
                            if self.is_holding_click:
                                print("[DEBUG] fishing(): Releasing mouse click")
                                self.mouse_controller.release(Button.left)
                                self.is_holding_click = False
                            
                            # Increment loop counter
                            self.fishing_loop_count += 1
                            print(f"[DEBUG] fishing(): fishing_loop_count = {self.fishing_loop_count}")
                            
                            # Check if we need to run auto-buy
                            loops_value = self.loops_per_purchase_var.get()
                            print(f"[DEBUG] fishing(): loops_value = {loops_value}")
                            if self.fishing_loop_count >= loops_value:
                                print("[DEBUG] fishing(): Loop count reached, running auto-buy...")
                                self.run_auto_buy_common_bait()
                                self.fishing_loop_count = 0
                                print("[DEBUG] fishing(): Auto-buy complete, loop count reset")
                            
                            # Run auto store devil fruit sequence
                            print("[DEBUG] fishing(): ***** CATCH COMPLETE - Calling check_and_store_devil_fruit() *****")
                            self.check_and_store_devil_fruit()
                            print("[DEBUG] fishing(): check_and_store_devil_fruit() returned")
                            
                            # Reset to casting state
                            print("[DEBUG] fishing(): Resetting state to IDLE for next cast")
                            self.fishing_state = "IDLE"
                            self.blue_lost_time = None
                            self.recast_locked = False
                            # Reset PID state
                            self.previous_error = 0
                            self.integral = 0
                            self.previous_time = None
                            print("[DEBUG] fishing(): State reset complete, returning to main loop")
                            return
                        else:
                            print(f"[DEBUG] fishing(): Delay NOT reached yet ({elapsed:.3f}s < {self.blue_lost_delay}s), waiting in recast_locked block")
                
                # Release click if holding when no color detected
                if self.is_holding_click:
                    print("[DEBUG] fishing(): Releasing mouse click (no blue detected)")
                    self.mouse_controller.release(Button.left)
                    self.is_holding_click = False
                
                # Reset PID state
                self.previous_error = 0
                self.integral = 0
                self.previous_time = None
                
        except Exception as e:
            print(f"Error in fishing: {e}")

    # Area selection
    def on_area_selected(self, bar_coords, drop_coords):
        """Callback when OverlaySelector is closed with selected coordinates"""
        self.bar_area = bar_coords
        self.drop_area = drop_coords
        
        # Save to settings
        self.settings["bar_area"] = bar_coords
        self.settings["drop_area"] = drop_coords
        self.save_settings()
        
        # Update area_box for backward compatibility
        self.area_box = bar_coords
        
        self.area_selector = None
        self.area_selector_active = False
        self.toggle_area_state = False
        self.buttons["toggle_area"].configure(fg_color="#3B8ED0", hover_color="#3B7ED0")

    def toggle_area(self):
        if self.start_stop_state:
            return
            
        self.toggle_area_state = not self.toggle_area_state
        
        if self.toggle_area_state:
            self.area_selector = OverlaySelector(
                self.root, 
                self.bar_area, 
                self.drop_area, 
                self.on_area_selected
            )
            self.buttons["toggle_area"].configure(fg_color="#339933", hover_color="#228B22")
        else:
            if self.area_selector:
                self.area_selector.close()
            self.area_selector_active = False
            self.toggle_area_state = False
            self.buttons["toggle_area"].configure(fg_color="#3B8ED0", hover_color="#3B7ED0")

    # Helpers
    def exit_app(self):
        if self.hotkey_listener:
            self.hotkey_listener.stop()
        if self.mouse_listener:
            self.mouse_listener.stop()
        if self.sct:
            self.sct.close()
        self.root.quit()
        os.kill(os.getpid(), signal.SIGTERM)

    def toggle_always_on_top(self):
        self.root.attributes("-topmost", self.always_on_top_var.get())

    def setup_spinbox_unfocus(self):
        """Set up unfocus binding for the spinbox to deselect it when clicking elsewhere"""
        # Find and store reference to the spinbox
        for widget in self.root.winfo_children():
            self._find_spinbox_and_bind(widget)

    def _find_spinbox_and_bind(self, widget):
        """Recursively find spinbox widgets and bind unfocus event"""
        if isinstance(widget, tk.Spinbox):
            # When clicking on spinbox, don't unfocus - this is handled by focus_set
            pass
        for child in widget.winfo_children():
            self._find_spinbox_and_bind(child)

    def on_root_click(self, event):
        """Handle clicks on the root window to [unfocus] spinbox"""
        # Check if click is on a spinbox
        widget = self.root.winfo_containing(event.x_root, event.y_root)
        if widget is None or not isinstance(widget, tk.Spinbox):
            # Click is elsewhere - unfocus any spinbox by focusing on root
            self.root.focus_set()

    def update_status(self):
        self.status_label.configure(
            text="RUNNING" if self.start_stop_state else "STOPPED",
            text_color="green" if self.start_stop_state else "red"
        )


if __name__ == "__main__":
    root = ctk.CTk()
    app = MacroApp(root)
    root.mainloop()