"""
Hand Gesture Windows Controller - Main Application.
Orchestrates computer vision, gesture classification, cursor smoothing,
multi-monitor management, and native Windows automation.
"""

import argparse
import sys
sys.stdout.reconfigure(encoding='utf-8')
import time
from typing import Optional, Tuple
import cv2
import numpy as np

from config import AppConfig, DEFAULT_CONFIG
from core.smoothing import CursorSmoother
from core.state_machine import GestureState, GestureStateMachine
from input_controller.hotkey_listener import GlobalHotkeyListener
from input_controller.mouse_controller import MouseController
from ui.hud_renderer import HUDRenderer
from vision.gesture_classifier import GestureClassifier
from vision.hand_detector import HandDetector, HandLandmarks
from window_manager.monitor_manager import MonitorManager
from window_manager.window_controller import WindowController


class GestureApp:
    """Master application controller."""

    def __init__(self, config: AppConfig = DEFAULT_CONFIG):
        self.cfg = config
        self.is_running = True

        # Initialize Subsystems
        print("[INIT] Initializing Monitor Manager...")
        self.monitor_mgr = MonitorManager(
            mode=self.cfg.monitors.mode,
            selected_index=self.cfg.monitors.selected_monitor_index,
        )
        print(f"       {self.monitor_mgr.get_summary_text()}")

        print("[INIT] Initializing Win32 Window Controller...")
        self.window_ctrl = WindowController()

        print("[INIT] Initializing Mouse Controller...")
        self.mouse_ctrl = MouseController()

        print("[INIT] Initializing MediaPipe Hand Detector...")
        self.detector = HandDetector(
            max_num_hands=self.cfg.hand.max_num_hands,
            min_detection_confidence=self.cfg.hand.min_detection_confidence,
            min_tracking_confidence=self.cfg.hand.min_tracking_confidence,
            model_complexity=self.cfg.hand.model_complexity,
        )

        print("[INIT] Initializing Gesture Classifier & State Machine...")
        self.classifier = GestureClassifier(
            pinch_threshold=self.cfg.gesture.pinch_threshold,
            pinch_release_threshold=self.cfg.gesture.pinch_release_threshold,
        )
        self.state_machine = GestureStateMachine(
            debounce_frames=self.cfg.gesture.click_debounce_frames,
        )

        print("[INIT] Initializing Cursor Smoother (1€ Filter)...")
        self.smoother = CursorSmoother(
            filter_type=self.cfg.smoothing.filter_type,
            min_cutoff=self.cfg.smoothing.min_cutoff,
            beta=self.cfg.smoothing.beta,
            d_cutoff=self.cfg.smoothing.d_cutoff,
            ema_alpha=self.cfg.smoothing.ema_alpha,
            deadzone_pixels=self.cfg.smoothing.deadzone_pixels,
            damping_radius=self.cfg.smoothing.damping_radius,
        )

        print("[INIT] Initializing HUD Overlay Engine...")
        self.hud = HUDRenderer(
            ui_config=self.cfg.ui,
            calib_config=self.cfg.calibration,
            monitor_mgr=self.monitor_mgr,
        )

        print("[INIT] Registering Global Emergency Hotkeys...")
        self.hotkeys = GlobalHotkeyListener(
            on_emergency_stop=self.stop,
            on_toggle_pause=self.toggle_pause,
            emergency_key=self.cfg.hotkeys.emergency_kill_key,
            pause_key=self.cfg.hotkeys.pause_toggle_key,
        )
        self.hotkeys.start()

        # Telemetry
        self.fps = 0.0
        self.last_frame_time = time.perf_counter()
        self.last_fist_toggle_time = 0.0
        self.fist_toggle_cooldown = 1.0
        self.smoothed_pos = (0, 0)
        self.raw_screen_pos = (0, 0)

    def run(self):
        """Main camera and control loop."""
        print("\n=======================================================")
        print("  GESTURE CONTROLLER RUNNING (Windows 11) - DUAL HAND SUPPORT")
        print("  Modes:")
        print("    🟢 1 MÃO: Dedo Indicador (👆) move o mouse.")
        print("    🟢 2 MÃOS (Recomendado!):")
        print("       👉 MÃO DIREITA (Navegação): Aponta o indicador para mover o mouse.")
        print("       👉 MÃO ESQUERDA (Gatilho / Ações):")
        print("          • ✌️ Dois Dedos ou 👌 Pinça -> Clique Esquerdo Simples")
        print("          • 🖐️ Mão Aberta            -> Segurar Clique & Arrastar (Hold Drag)")
        print("    🔒 TRAVA DE PAUSA GERAL:")
        print("       • ✊ Punho Fechado (Qualquer Mão) -> Trava / Destrava Todo o Controle")
        print("  Controls:")
        print(f"    [{self.cfg.hotkeys.emergency_kill_key.upper()}] Emergency Stop | [{self.cfg.hotkeys.pause_toggle_key.upper()}] Pause / Resume")
        print("    [M] Cycle Monitor Mode | [D] Toggle HUD Overlays")
        print("=======================================================\n")

        cap = cv2.VideoCapture(self.cfg.camera.camera_id)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.cfg.camera.frame_width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.cfg.camera.frame_height)
        cap.set(cv2.CAP_PROP_FPS, self.cfg.camera.target_fps)

        if not cap.isOpened():
            print(f"[ERROR] Could not open camera {self.cfg.camera.camera_id}. Please check device connection.")
            return

        try:
            while self.is_running:
                loop_start = time.perf_counter()
                success, frame = cap.read()
                if not success or frame is None:
                    time.sleep(0.01)
                    continue

                if self.cfg.camera.flip_horizontal:
                    frame = cv2.flip(frame, 1)

                h, w, _ = frame.shape

                # 1. Vision - Detect All Hand Landmarks (Multi-Hand)
                hands = self.detector.process_hands(frame)

                cursor_hand = None
                action_hand = None

                # Check if ANY hand is making a Closed Fist (✊) to Toggle Pause / Resume
                if len(hands) > 0:
                    is_any_fist = any(self.classifier.classify(h)[0] == GestureState.FIST for h in hands)
                    if is_any_fist and (loop_start - self.last_fist_toggle_time) >= self.fist_toggle_cooldown:
                        self.last_fist_toggle_time = loop_start
                        self.toggle_pause()

                is_paused = self.state_machine.is_paused

                # 2. Dynamic Hand Assignment by Hand Count:
                # - 1 Hand on screen: ALWAYS controls the cursor (full screen traversal)
                # - 2 Hands on screen: Leftmost hand = Click/Actions, Rightmost hand = Cursor control
                if len(hands) == 1:
                    cursor_hand = hands[0]
                elif len(hands) >= 2:
                    sorted_hands = sorted(hands, key=lambda h: h.landmarks[0].px)
                    action_hand = sorted_hands[0]   # Hand on the left side of frame
                    cursor_hand = sorted_hands[-1]  # Hand on the right side of frame

                # 3. Action / Click Processing (Exclusively from Left/Action Hand)
                if not is_paused and action_hand is not None:
                    raw_gesture, metrics = self.classifier.classify(action_hand)
                    state_info = self.state_machine.update(raw_gesture)
                else:
                    metrics = None
                    fallback_state = GestureState.FIST if is_paused else GestureState.POINTING
                    state_info = self.state_machine.update(fallback_state)

                current_state = state_info["state"]
                action = state_info["action"]
                is_mouse_down = state_info["is_mouse_down"]
                is_paused = state_info["is_paused"]

                # 4. Cursor Movement Processing (Exclusively from Right/Cursor Hand)
                if not is_paused and cursor_hand is not None:
                    index_tip = cursor_hand.landmarks[8]
                    norm_x, norm_y = self._map_roi_coordinates(index_tip.px, index_tip.py, w, h)
                    screen_x, screen_y = self.monitor_mgr.map_normalized_to_screen(norm_x, norm_y)
                    self.raw_screen_pos = (screen_x, screen_y)
                    self.smoothed_pos = self.smoother.smooth(
                        screen_x, screen_y, timestamp=loop_start
                    )
                else:
                    # Paused or Right hand not visible -> Cursor stays locked, no jumping!
                    self.smoother.reset()

                # 5. Input Automation
                if not is_paused and self.smoothed_pos != (0, 0):
                    if action == "mouse_move":
                        if cursor_hand is not None:
                            self.mouse_ctrl.move_to(self.smoothed_pos[0], self.smoothed_pos[1])
                    elif action in ("click", "mouse_down", "mouse_drag", "mouse_up"):
                        self._handle_input_actions(action, self.smoothed_pos)

                if len(hands) == 0 or is_paused:
                    if is_mouse_down:
                        self.mouse_ctrl.release_all()

                # 6. Render HUD and Visuals
                hud_frame = self.hud.render(
                    frame=frame,
                    hand=cursor_hand,
                    current_state=current_state,
                    action=action,
                    is_mouse_down=is_mouse_down,
                    is_paused=is_paused,
                    screen_pos=self.raw_screen_pos,
                    smoothed_pos=self.smoothed_pos,
                    fps=self.fps,
                    metrics=metrics,
                )

                # Draw MediaPipe skeletal wireframes with clear role labels
                if self.cfg.ui.show_landmarks:
                    if cursor_hand is not None:
                        self.detector.draw_landmarks(hud_frame, cursor_hand, color_custom=(50, 220, 50))
                        wrist = cursor_hand.landmarks[0]
                        label = "CURSOR (MOUSE)" if len(hands) == 1 else "CURSOR [DIR]"
                        cv2.putText(hud_frame, label, (wrist.px - 35, wrist.py + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (50, 220, 50), 1, cv2.LINE_AA)
                    if action_hand is not None:
                        self.detector.draw_landmarks(hud_frame, action_hand, color_custom=(0, 165, 255))
                        wrist = action_hand.landmarks[0]
                        cv2.putText(hud_frame, "CLIQUE / ACAO [ESQ]", (wrist.px - 35, wrist.py + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 165, 255), 1, cv2.LINE_AA)

                cv2.imshow(self.cfg.ui.window_name, hud_frame)

                # 7. Check OpenCV Window Key Events
                key = cv2.waitKey(1) & 0xFF
                if key in (27, ord("q"), ord("Q")):  # ESC or Q
                    print("\n[INFO] Exit key pressed in HUD window.")
                    break
                elif key in (ord("p"), ord("P"), 32):  # P or SPACE
                    self.toggle_pause()
                elif key in (ord("m"), ord("M")):
                    new_mode = self.monitor_mgr.cycle_mode()
                    print(f"[MODE] Switched monitor mode to: {new_mode}")
                elif key in (ord("d"), ord("D")):
                    self.cfg.ui.show_hud = not self.cfg.ui.show_hud

                # Compute frame rate
                now = time.perf_counter()
                dt = now - self.last_frame_time
                if dt > 0:
                    current_fps = 1.0 / dt
                    self.fps = 0.9 * self.fps + 0.1 * current_fps if self.fps > 0 else current_fps
                self.last_frame_time = now

        except KeyboardInterrupt:
            print("\n[INFO] Stopped by user (KeyboardInterrupt).")

        finally:
            self.shutdown(cap)

    def _map_roi_coordinates(self, px: int, py: int, frame_w: int, frame_h: int) -> Tuple[float, float]:
        """Convert pixel position within camera frame into normalized [0.0, 1.0] ROI coordinates with speed multiplier."""
        x_min = self.cfg.calibration.margin_x_min * frame_w
        x_max = self.cfg.calibration.margin_x_max * frame_w
        y_min = self.cfg.calibration.margin_y_min * frame_h
        y_max = self.cfg.calibration.margin_y_max * frame_h

        roi_w = max(1.0, x_max - x_min)
        roi_h = max(1.0, y_max - y_min)

        # Center-relative normalized coordinates [-0.5, +0.5]
        center_x = (x_min + x_max) / 2.0
        center_y = (y_min + y_max) / 2.0

        rel_x = (px - center_x) / roi_w
        rel_y = (py - center_y) / roi_h

        # Apply speed multiplier so cursor traverses full screen faster and without hand reaching camera borders
        mult = getattr(self.cfg.calibration, "speed_multiplier", 1.35)
        rel_x *= mult
        rel_y *= mult

        norm_x = rel_x + 0.5
        norm_y = rel_y + 0.5

        # Clamp to [0.0, 1.0]
        return max(0.0, min(1.0, norm_x)), max(0.0, min(1.0, norm_y))

    def _handle_input_actions(self, action: str, pos: Tuple[int, int]):
        """Dispatch actions to mouse and window subsystems."""
        target_x, target_y = pos

        if action == "mouse_move":
            # Pointing gesture -> standard cursor motion
            self.mouse_ctrl.move_to(target_x, target_y)

        elif action == "click":
            # Dedicated instant single left click (Zero unwanted dragging)
            self.mouse_ctrl.click(target_x, target_y)

        elif action == "mouse_down":
            # Open hand -> left click down / start hold drag
            self.mouse_ctrl.mouse_down(target_x, target_y)

        elif action == "mouse_drag":
            # Sustained open hand -> move cursor with button held down (drags window/element)
            self.mouse_ctrl.move_to(target_x, target_y)

        elif action == "mouse_up":
            # Release open hand -> drop drag / release click
            self.mouse_ctrl.mouse_up(target_x, target_y)

    def toggle_pause(self):
        """Toggle active gesture processing."""
        paused = self.state_machine.toggle_pause()
        if paused:
            self.mouse_ctrl.release_all()
            print("[STATUS] Gesture control PAUSED (Safety Lock Active)")
        else:
            print("[STATUS] Gesture control RESUMED (Active)")

    def stop(self):
        """Emergency killswitch handler."""
        print("\n[SAFETY] Emergency Killswitch Triggered! Exiting immediately...")
        self.is_running = False

    def shutdown(self, cap: Optional[cv2.VideoCapture] = None):
        """Safely release all hardware, input, and OS resources."""
        print("[SHUTDOWN] Releasing all resources...")
        self.is_running = False

        if self.mouse_ctrl:
            self.mouse_ctrl.release_all()

        if self.hotkeys:
            self.hotkeys.stop()

        if cap and cap.isOpened():
            cap.release()

        if self.detector:
            self.detector.close()

        cv2.destroyAllWindows()
        print("[SHUTDOWN] Clean exit complete.")


def parse_arguments() -> AppConfig:
    """Parse command-line arguments and override configuration."""
    parser = argparse.ArgumentParser(
        description="Hand Gesture Windows Controller (Windows 11 Multi-Monitor)"
    )
    parser.add_argument(
        "--camera", type=int, default=0, help="Camera device index (default: 0)"
    )
    parser.add_argument(
        "--filter",
        type=str,
        choices=["one_euro", "ema"],
        default="one_euro",
        help="Smoothing filter algorithm (default: one_euro)",
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["span_all", "primary_only"],
        default="span_all",
        help="Multi-monitor mapping mode (default: span_all)",
    )
    parser.add_argument(
        "--no-landmarks",
        action="store_true",
        help="Disable drawing skeletal wireframe on HUD",
    )
    parser.add_argument(
        "--min-cutoff",
        type=float,
        default=0.05,
        help="1€ Filter min_cutoff parameter for jitter reduction (default: 0.05)",
    )
    parser.add_argument(
        "--beta",
        type=float,
        default=0.08,
        help="1€ Filter beta parameter for high-speed responsiveness (default: 0.08)",
    )

    args = parser.parse_args()

    cfg = AppConfig()
    cfg.camera.camera_id = args.camera
    cfg.smoothing.filter_type = args.filter
    cfg.smoothing.min_cutoff = args.min_cutoff
    cfg.smoothing.beta = args.beta
    cfg.monitors.mode = args.mode
    if args.no_landmarks:
        cfg.ui.show_landmarks = False

    return cfg


if __name__ == "__main__":
    config = parse_arguments()
    app = GestureApp(config)
    app.run()
