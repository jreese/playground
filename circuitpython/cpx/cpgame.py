"""
Simple CircuitPython "game" framework.
Uses decorators for defining behavior via callbacks.

Decorators:

  @tick - Run a function at every tick of the framework
  @every(t: int) - Run a function every x seconds

  @on(*b: pin, action=DOWN) - Run a function on button press

Framework functions:

  at(t: int) - Run a function at monotonic time t
  after(t: int) - Run a function after monotic time t from now

  start() - Start the main event loop
  stop() - Stop the main event loop

"""

import gamepad
import time

from digitalio import DigitalInOut, Direction, Pull

# External constants

DOWN = 1
UP = 2
PROPOGATE = object()

# Internal state

RUNNING = True
INTERVALS = {}
TIMERS = {}
BUTTONS = []
DIOS = []
PRESSES = []


def tick(fn):
    INTERVALS[fn] = (0, 0)
    return fn

def every(interval):
    def wrapper(fn):
        INTERVALS[fn] = (interval, 0)
        return fn
    return wrapper

def at(target, fn):
    TIMERS[fn] = target

def after(target, fn):
    TIMERS[fn] = time.monotonic() + target

def on(*buttons, action=DOWN):
    global GAMEPAD

    for button in buttons:
        if button not in BUTTONS:
            dio = DigitalInOut(button)
            dio.direction = Direction.INPUT
            dio.pull = Pull.DOWN
            BUTTONS.append(button)
            DIOS.append(dio)
    
    value = tuple(buttons)

    def wrapper(fn):
        PRESSES.append((fn, buttons, action))
        return fn
    return wrapper

def stop():
    global RUNNING
    RUNNING = False

def start():
    if PRESSES:
        every(0.02)(Gamepad())

    while True:
        if not TIMERS and not INTERVALS:
            print("No functions registered, quitting")
            return 0

        now = time.monotonic()
        for fn, (interval, last_called) in INTERVALS.items():
            target = last_called + interval
            if target <= now:
                fn(now)
                INTERVALS[fn] = (interval, now)
                target += interval

        for fn, target in TIMERS.items():
            if target <= now:
                del TIMERS[fn]
                fn(now)

        next_target = min(
            [last_called + interval for last_called, interval in INTERVALS.values()] +
            [target for target in TIMERS.values()]
        )

        while True:
            slp = next_target - time.monotonic()
            if slp > 0:
                # print("Sleeping for {} seconds".format(slp))
                time.sleep(slp)
            else:
                break
    
class Gamepad:
    def __init__(self):
        self.down = ()
        self.pressed = []
        
    def __call__(self, now):
        down = tuple(button for button, dio in zip(BUTTONS, DIOS) if dio.value)
        if down != self.down:
            self.down = down
            return

        fresh_down = [b for b in down if b not in self.pressed]
        fresh_up = [b for b in self.pressed if b not in down]

        if fresh_down:
            # print("fresh down: {}".format(fresh_down))
            self.pressed.extend(fresh_down)

        if fresh_up:
            # print("fresh up: {}".format(fresh_up))
            for btn in fresh_up:
                self.pressed.remove(btn)

        if not (fresh_down or fresh_up):
            return 

        for (fn, buttons, action) in PRESSES:
            if action == DOWN and all(b in fresh_down for b in buttons):
                v = fn(now)
            elif action == UP and all(b in fresh_up for b in buttons):
                v = fn(now)
            else:
                v = PROPOGATE

            if v is not PROPOGATE:
                break

