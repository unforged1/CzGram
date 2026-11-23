"""A small pixel creature drawn with canvas rectangles (no image files, little memory)."""
import sys

FONT = "Helvetica Neue" if sys.platform == "darwin" else "DejaVu Sans"

CELL = 4
COLS, ROWS = 15, 14
WIDTH, HEIGHT = COLS * CELL, ROWS * CELL
BODY = "#D97757"
SHADE = "#B95F42"
DARK = "#1F1E1D"
SPINNER = "·✢✳✶✻✽✻✶✳✢"
TICK_MS = 125
BLUE_BODY = "#4FA8FF"
BLUE_SHADE = "#2B6FD6"
BLUE_DARK = "#0B1830"
FLAME = ("#E3F6FF", "#8FD6FF", "#3F9BFF")
LAPTOP_LID = "#3A3D44"
LAPTOP_BASE = "#9AA0A8"
SCREEN_TEXT = ("#9AD8FF", "#E3F6FF", "#5FB4F0")
SWEAT = "#8FD6FF"


class Mascot:
    """States: idle, busy, think, talk, wave, sad, laptop (bulk mode: typing flat out). Call start()/stop() as the bar shows or hides.

    `rest` is the state it settles back into: "busy" while quick mode is running.
    """

    def __init__(self, canvas, on_tick=None):
        self.c = canvas
        self.state = "idle"
        self.rest = "idle"
        self.t = 0
        self.job = None
        self.on_tick = on_tick
        self.running = False  # speed mode: blue, on fire, and in a hurry

    def set_state(self, state):
        if state != self.state:
            self.state = state
            self.t = 0
            self.draw()

    def set_running(self, running):
        if running != self.running:
            self.running = running
            self.draw()

    def start(self):
        if self.job is None:
            self._tick()

    def stop(self):
        if self.job is not None:
            self.c.after_cancel(self.job)
            self.job = None

    def _tick(self):
        self.t += 1
        if self.state == "wave" and self.t > 14:
            self.state = self.rest
        self.draw()
        if self.on_tick:
            self.on_tick()
        self.job = self.c.after(TICK_MS, self._tick)

    def _rect(self, x, y, w, h, color):
        self.c.create_rectangle(x * CELL, y * CELL, (x + w) * CELL, (y + h) * CELL,
                                fill=color, outline="")

    def _draw_running(self):
        """Mid-sprint and leaning forward, with blue flames on its back and a trail behind."""
        t, state = self.t, self.state
        top = 5 + t % 2
        # Galloping legs: each pair swings forward and back in turn.
        swing = (-1, 0, 1, 0)[t % 4]
        for i, x in enumerate((5, 7, 9, 11)):
            offset = swing if i % 2 else -swing
            self._rect(x + offset, top + 6, 1, 2 if offset == 0 else 1, BLUE_SHADE)
        self._rect(4, top, 9, 6, BLUE_BODY)
        # Pumping arms, the back one high when the front one is low.
        self._rect(2, top + 1 + t % 2, 2, 2, BLUE_BODY)
        self._rect(13, top + 2 - t % 2, 2, 2, BLUE_BODY)
        # Eyes fixed on the road ahead.
        look = 1 if state != "think" else (0, 1)[(t // 2) % 2]
        self._rect(8 + look, top + 1, 1, 2, BLUE_DARK)
        self._rect(11 + look - 1, top + 1, 1, 2, BLUE_DARK)
        if state == "talk" and t % 3:
            self._rect(10, top + 4, 1, 1, BLUE_DARK)
        # Flames along the back, tallest at the rear, flickering with the stride.
        for i, x in enumerate((4, 5, 6, 7, 8, 9)):
            height = max(1, 3 - i // 2 - (t + i * 2) % 3 // 2)
            if top - height >= 0:
                self._rect(x, top - height, 1, height, FLAME[(t + i) % 3])
        # Sparks trailing behind.
        for i, y in enumerate((top + 1, top + 3, top + 5)):
            if (t + i) % 3:
                self._rect((t + i * 2) % 2, y, 1, 1, FLAME[(t + i) % 3])

    def _draw_laptop(self):
        """Hunched behind a laptop, hammering the keys, eyes racing along the lines."""
        t = self.t
        body, shade, dark = (BLUE_BODY, BLUE_SHADE, BLUE_DARK) if self.running else (BODY, SHADE, DARK)
        top = 2 + t % 2                      # quick jittery bounce
        self._rect(3, top, 9, 6, body)       # body, its lower half hidden by the lid
        # Eyes flick left to right across the screen, faster than the busy state.
        shift = (-1, 0, 1, 1)[t % 4]
        self._rect(5 + shift, top + 1, 1, 2, dark)
        self._rect(9 + shift, top + 1, 1, 2, dark)
        # Sweat drop and speed streaks: this is bulk mode, everything at once.
        if t % 6 < 3:
            self._rect(12, top - 1 + t % 3, 1, 1, SWEAT)
        for i, y in enumerate((top + 1, top + 3, top + 5)):
            if (t + i) % 2:
                self._rect(0, y, 1 + (t + i) % 2, 1, SWEAT)
        # Laptop: lid facing us with scrolling "text", then the keyboard deck.
        self._rect(4, 7, 7, 5, LAPTOP_LID)
        for row in range(3):
            width = 2 + (t * 3 + row * 5) % 4
            self._rect(5, 8 + row, width, 1, SCREEN_TEXT[(t + row) % 3])
        self._rect(2, 12, 11, 1, LAPTOP_BASE)
        # Hands on the keys, taking turns every tick.
        self._rect(2 + t % 2, 11 - t % 2, 2, 1, body)
        self._rect(11 - (t + 1) % 2, 11 - (t + 1) % 2, 2, 1, body)
        self.c.create_text(WIDTH - 5, 6, text=SPINNER[(t * 2) % len(SPINNER)], fill=body, font=("DejaVu Sans", 9))

    def draw(self):
        c, t, state = self.c, self.t, self.state
        c.delete("all")
        if state == "laptop":
            self._draw_laptop()
            return
        if self.running and state != "sad":
            self._draw_running()
            return
        body, shade, dark = (BLUE_BODY, BLUE_SHADE, BLUE_DARK) if self.running else (BODY, SHADE, DARK)
        top = 3
        if state in ("talk", "wave"):
            top += (t // 2) % 2  # lively bob
        elif state == "idle":
            top += 1 if (t // 6) % 2 else 0  # slow breathing
        elif state == "think":
            top += 1 if (t // 3) % 2 else 0
        elif state == "busy":
            top += t % 2  # hurried bounce

        # Legs. They alternate slightly while talking so the creature shuffles.
        step = t % 2 if state == "busy" else (t // 2) % 2 if state == "talk" else 0
        legs_y = top + 6
        for i, x in enumerate((4, 6, 8, 10)):
            self._rect(x, legs_y, 1, 2 - (step if i % 2 == 0 else 1 - step)
                       if state in ("talk", "busy") else 2, shade)

        self._rect(3, top, 9, 6, body)  # body

        # Arms
        left_y, right_y = top + 2, top + 2
        if state == "talk":
            left_y -= (t // 2) % 2
            right_y -= ((t // 2) + 1) % 2
        elif state == "busy":  # both arms hammering away in turn
            left_y -= t % 2
            right_y -= (t + 1) % 2
        elif state == "wave":
            right_y -= 2 if (t // 2) % 2 else 1
        elif state == "sad":
            left_y += 1
            right_y += 1
        self._rect(1, left_y, 2, 2, body)
        self._rect(12, right_y, 2, 2, body)

        # Eyes
        eye_h = 2
        shift = 0
        if state == "idle" and t % 28 in (0, 1):
            eye_h = 0  # blink
        elif state == "think":
            shift = (-1, 0, 1, 0)[(t // 4) % 4]
        elif state == "busy":
            shift = (-1, 0, 1, 0)[(t // 2) % 4]  # eyes darting along the page
        elif state == "sad":
            eye_h = 1
        ey = top + 1 + (2 - eye_h if state == "sad" else 0)
        if eye_h:
            self._rect(5 + shift, ey, 1, eye_h, dark)
            self._rect(9 + shift, ey, 1, eye_h, dark)
        else:
            self._rect(5, top + 2, 1, 1, shade)
            self._rect(9, top + 2, 1, 1, shade)

        # Mouth opens and closes while talking
        if state == "talk" and t % 3:
            self._rect(7, top + 4, 1, 1, dark)

        if state in ("think", "busy"):
            c.create_text(WIDTH - 5, 6, text=SPINNER[t % len(SPINNER)], fill=body,
                          font=(FONT, 9))
