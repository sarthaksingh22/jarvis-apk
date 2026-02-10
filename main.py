# ==========================================================
#                 FINAL JARVIS – COMPLETE
# AR Hologram + 3D HUD + Voice + Gestures + Data Panels
# ==========================================================

import cv2, mediapipe as mp, math, random, threading, webbrowser, time
import numpy as np
import speech_recognition as sr
import pyttsx3

from kivy.app import App
from kivy.clock import Clock
from kivy.graphics import Color, Ellipse, Line, Rectangle, PushMatrix, PopMatrix, Rotate
from kivy.graphics.texture import Texture
from kivy.uix.widget import Widget


# ---------------- VOICE ----------------
engine = pyttsx3.init()
engine.setProperty("rate", 170)

def speak(text):
    engine.say(text)
    engine.runAndWait()


# ---------------- GLOBAL STATES ----------------
hologram_visible = True


# ---------------- DATA PANELS ----------------
panels = []

def create_panel(title, value):
    panels.append({
        "title": title,
        "value": value,
        "x": -300,
        "y": random.randint(-80, 80),
        "alpha": 0,
        "scale": 0.5,
        "life": 180
    })


# ---------------- ACTION ENGINE ----------------
def perform_action(action):
    global hologram_visible

    if action == "video":
        speak("Opening holographic video.")
        webbrowser.open("https://youtube.com/results?search_query=iron+man+hologram")

    elif action == "hologram_on":
        hologram_visible = True
        speak("Hologram activated.")

    elif action == "hologram_off":
        hologram_visible = False
        speak("Hologram hidden.")

    elif action == "show_panels":
        speak("Displaying system data.")
        create_panel("AI STATUS", "ONLINE")
        create_panel("CAMERA", "ACTIVE")
        create_panel("HUD MODE", "IRON-MAN")


# ---------------- CAMERA ----------------
cam = cv2.VideoCapture(0)

def get_camera_texture():
    ret, frame = cam.read()
    if not ret:
        return None

    frame = cv2.flip(frame, 1)
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    texture = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt="rgb")
    texture.blit_buffer(frame.tobytes(), colorfmt="rgb", bufferfmt="ubyte")
    return texture


# ---------------- HAND TRACKING ----------------
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=1)

pinch_start_time = None
pinching = False


def detect_gesture():
    global pinching, pinch_start_time

    ret, frame = cam.read()
    if not ret:
        return None

    frame = cv2.flip(frame, 1)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = hands.process(rgb)

    if not result.multi_hand_landmarks:
        pinching = False
        return None

    lm = result.multi_hand_landmarks[0].landmark
    thumb, index = lm[4], lm[8]

    pinch_dist = abs(thumb.x - index.x) + abs(thumb.y - index.y)
    x, y = index.x, index.y

    # PINCH START
    if pinch_dist < 0.04:

        if not pinching:
            pinching = True
            pinch_start_time = time.time()
            start_pos = (x, y)
            detect_gesture.start_pos = start_pos
            return None

        dx = x - detect_gesture.start_pos[0]
        dy = y - detect_gesture.start_pos[1]

        # HOLD → SHOW PANELS
        if time.time() - pinch_start_time > 1.5:
            pinching = False
            return "show_panels"

        # DRAG RIGHT → VIDEO
        if dx > 0.15:
            pinching = False
            return "video"

        # DRAG UP → HOLOGRAM ON
        if dy < -0.15:
            pinching = False
            return "hologram_on"

        # DRAG DOWN → HOLOGRAM OFF
        if dy > 0.15:
            pinching = False
            return "hologram_off"

    else:
        pinching = False

    return None


# ---------------- PARTICLES ----------------
particles = [
    {"a": random.random() * 360, "r": random.randint(60, 160), "s": random.random() * 2}
    for _ in range(80)
]


# ---------------- AR HUD ----------------
class ARHologram(Widget):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.angle = 0

    def update(self, dt):
        global hologram_visible

        self.canvas.clear()

        # CAMERA BACKGROUND
        texture = get_camera_texture()
        if texture:
            with self.canvas:
                Rectangle(texture=texture, pos=self.pos, size=self.size)

        # GESTURE
        action = detect_gesture()
        if action:
            perform_action(action)

        if not hologram_visible:
            return

        cx, cy = self.center
        self.angle += 1.5

        with self.canvas:

            # DEPTH GLOW
            Color(0, 1, 1, 0.08)
            Ellipse(pos=(cx - 200, cy - 200), size=(400, 400))

            Color(0, 1, 1, 0.15)
            Ellipse(pos=(cx - 150, cy - 150), size=(300, 300))

            # RINGS
            Color(0, 1, 1, 0.9)
            Line(circle=(cx, cy, 140), width=1.4)
            Line(circle=(cx, cy, 100), width=1.2)
            Line(circle=(cx, cy, 60), width=1)

            # ROTATING CORE
            PushMatrix()
            Rotate(angle=self.angle, origin=(cx, cy))
            Color(0, 1, 1, 0.35)
            Ellipse(pos=(cx - 40, cy - 40), size=(80, 80))
            Color(0, 1, 1, 1)
            Ellipse(pos=(cx - 12, cy - 12), size=(24, 24))
            PopMatrix()

            # PARTICLES
            for p in particles:
                p["a"] += p["s"]
                rad = math.radians(p["a"])
                px = cx + math.cos(rad) * p["r"]
                py = cy + math.sin(rad) * p["r"]
                Color(0, 1, 1, 0.85)
                Ellipse(pos=(px, py), size=(3, 3))

            # -------- DATA PANELS --------
            for p in panels[:]:

                p["x"] += 8
                p["alpha"] = min(0.9, p["alpha"] + 0.03)
                p["scale"] = min(1.0, p["scale"] + 0.02)

                px = cx + 180 + p["x"]
                py = cy + p["y"]

                Color(0, 1, 1, p["alpha"] * 0.15)
                Rectangle(pos=(px, py), size=(180 * p["scale"], 80 * p["scale"]))

                Color(0, 1, 1, p["alpha"])
                Line(rectangle=(px, py, 180 * p["scale"], 80 * p["scale"]), width=1.2)

                p["life"] -= 1
                if p["life"] <= 0:
                    panels.remove(p)


# ---------------- VOICE LOOP ----------------
rec = sr.Recognizer()
mic = sr.Microphone()

def voice_loop():
    speak("Jarvis online.")

    while True:
        try:
            with mic as src:
                audio = rec.listen(src, phrase_time_limit=4)

            text = rec.recognize_google(audio).lower()

            if "hey jarvis" in text:
                speak("Yes Sir.")

            elif "show video" in text:
                perform_action("video")

            elif "hide hologram" in text:
                perform_action("hologram_off")

            elif "activate hologram" in text:
                perform_action("hologram_on")

            elif "show panels" in text or "show system data" in text:
                perform_action("show_panels")

        except:
            pass


# ---------------- APP ----------------
class JarvisAR(App):

    def build(self):
        root = ARHologram()
        Clock.schedule_interval(root.update, 1 / 30)
        threading.Thread(target=voice_loop, daemon=True).start()
        return root


if __name__ == "__main__":
    JarvisAR().run()
