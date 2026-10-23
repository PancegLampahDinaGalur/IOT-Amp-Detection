"""
Parametric enclosure for the Raspberry Pi / ESP32 current-monitor project.

Open this file from FreeCAD with View -> Panels -> Python console, then run:
    exec(open(r"C:\path\to\freecad_enclosure.py").read())

The dimensions near the top are intentionally easy to edit.  The model is a
prototype based on common Raspberry Pi 4/5 and ESP32 DevKit board sizes; check
the real parts before printing.
"""

import FreeCAD as App
import Part


# ------------------------------ Main parameters -----------------------------
BOX_L = 220.0
BOX_W = 140.0
BOX_H = 70.0
WALL = 3.0
BOTTOM = 3.0

COVER_THICKNESS = 3.0
COVER_OVERLAP = 1.5
SCREW_DIAMETER = 3.2
STANDOFF_DIAMETER = 8.0
STANDOFF_HEIGHT = 8.0

# Component envelopes (replace these after measuring the actual parts).
RASPI_L, RASPI_W, RASPI_H = 85.0, 56.0, 18.0
ESP32_L, ESP32_W, ESP32_H = 52.0, 28.0, 12.0
PSU_L, PSU_W, PSU_H = 100.0, 50.0, 32.0
TERMINAL_L, TERMINAL_W, TERMINAL_H = 60.0, 25.0, 22.0

# Component positions measured from the inside bottom-left corner.
RASPI_X, RASPI_Y = 15.0, 15.0
ESP32_X, ESP32_Y = 125.0, 15.0
PSU_X, PSU_Y = 15.0, 85.0
TERMINAL_X, TERMINAL_Y = 135.0, 88.0


def feature(doc, name, label, shape, color):
    obj = doc.addObject("Part::Feature", name)
    obj.Label = label
    obj.Shape = shape
    if obj.ViewObject is not None:
        obj.ViewObject.ShapeColor = color
    return obj


def box_envelope(doc, name, label, x, y, length, width, height, color):
    shape = Part.makeBox(length, width, height, App.Vector(x, y, BOTTOM))
    obj = feature(doc, name, label, shape, color)
    if obj.ViewObject is not None:
        obj.ViewObject.Transparency = 75
    return obj


def add_standoffs(doc, group, x, y, length, width, hole_positions):
    for index, (dx, dy) in enumerate(hole_positions, 1):
        px = x + dx
        py = y + dy
        outer = Part.makeCylinder(
            STANDOFF_DIAMETER / 2.0,
            STANDOFF_HEIGHT,
            App.Vector(px, py, BOTTOM),
        )
        bore = Part.makeCylinder(
            SCREW_DIAMETER / 2.0,
            STANDOFF_HEIGHT,
            App.Vector(px, py, BOTTOM),
        )
        obj = feature(
            doc,
            "Standoff_%s_%s" % (group, index),
            "%s standoff %s" % (group, index),
            outer.cut(bore),
            (0.75, 0.75, 0.78),
        )
        obj.addProperty("App::PropertyString", "Purpose", "Documentation")
        obj.Purpose = "Use M3 screw or heat-set insert"


def make_vent_slots():
    vents = None
    for row in range(3):
        for column in range(7):
            slot = Part.makeBox(
                18.0,
                3.0,
                2.5,
                App.Vector(113.0 + column * 20.0, 47.0 + row * 7.0, BOX_H),
            )
            vents = slot if vents is None else vents.fuse(slot)
    return vents


def create_model():
    try:
        App.closeDocument("AmpDetc_Enclosure")
    except Exception:
        pass

    doc = App.newDocument("AmpDetc_Enclosure")

    parameters = doc.addObject("App::FeaturePython", "Parameters")
    parameters.Label = "EDIT THESE PARAMETERS (millimetres)"
    for name, value in (
        ("BoxLength", BOX_L),
        ("BoxWidth", BOX_W),
        ("BoxHeight", BOX_H),
        ("WallThickness", WALL),
        ("BottomThickness", BOTTOM),
        ("CoverThickness", COVER_THICKNESS),
        ("RaspberryLength", RASPI_L),
        ("RaspberryWidth", RASPI_W),
        ("Esp32Length", ESP32_L),
        ("Esp32Width", ESP32_W),
        ("PowerSupplyLength", PSU_L),
        ("PowerSupplyWidth", PSU_W),
        ("TerminalLength", TERMINAL_L),
        ("TerminalWidth", TERMINAL_W),
    ):
        parameters.addProperty("App::PropertyLength", name, "Dimensions")
        setattr(parameters, name, value)
    parameters.addProperty("App::PropertyString", "Notes", "Documentation")
    parameters.Notes = (
        "Prototype layout. Measure actual boards, PSU, terminal and connectors "
        "before printing. Edit constants in this script and run it again."
    )

    outer = Part.makeBox(BOX_L, BOX_W, BOX_H)
    cavity = Part.makeBox(
        BOX_L - 2 * WALL,
        BOX_W - 2 * WALL,
        BOX_H,
        App.Vector(WALL, WALL, BOTTOM),
    )
    base_shape = outer.cut(cavity)

    # Front opening for the power cable; right opening for control/sensor cable.
    power_opening = Part.makeBox(
        35.0, WALL + 2.0, 14.0, App.Vector(18.0, -1.0, 12.0)
    )
    control_opening = Part.makeBox(
        WALL + 2.0, 42.0, 14.0, App.Vector(BOX_L - WALL - 1.0, 82.0, 14.0)
    )
    terminal_opening = Part.makeBox(
        68.0, WALL + 2.0, 18.0, App.Vector(128.0, -1.0, 30.0)
    )
    base_shape = base_shape.cut(power_opening)
    base_shape = base_shape.cut(control_opening)
    base_shape = base_shape.cut(terminal_opening)
    base = feature(doc, "Base", "Enclosure base", base_shape, (0.35, 0.38, 0.42))

    cover = Part.makeBox(
        BOX_L,
        BOX_W,
        COVER_THICKNESS,
        App.Vector(0, 0, BOX_H),
    )
    cover_holes = None
    for x, y in (
        (8.0, 8.0),
        (BOX_L - 8.0, 8.0),
        (8.0, BOX_W - 8.0),
        (BOX_L - 8.0, BOX_W - 8.0),
    ):
        hole = Part.makeCylinder(
            SCREW_DIAMETER / 2.0,
            COVER_THICKNESS + 2.0,
            App.Vector(x, y, BOX_H - 1.0),
        )
        cover_holes = hole if cover_holes is None else cover_holes.fuse(hole)
    cover = cover.cut(cover_holes).cut(make_vent_slots())
    feature(doc, "Cover", "Ventilated screw-on cover", cover, (0.45, 0.48, 0.52))

    raspberry = box_envelope(
        doc, "RaspberryPiEnvelope", "Raspberry Pi envelope", RASPI_X, RASPI_Y,
        RASPI_L, RASPI_W, RASPI_H, (0.20, 0.55, 0.25),
    )
    esp32 = box_envelope(
        doc, "Esp32Envelope", "ESP32 DevKit envelope", ESP32_X, ESP32_Y,
        ESP32_L, ESP32_W, ESP32_H, (0.20, 0.35, 0.80),
    )
    psu = box_envelope(
        doc, "PowerSupplyEnvelope", "Power supply envelope", PSU_X, PSU_Y,
        PSU_L, PSU_W, PSU_H, (0.80, 0.45, 0.15),
    )
    terminal = box_envelope(
        doc, "TerminalEnvelope", "Terminal block envelope", TERMINAL_X, TERMINAL_Y,
        TERMINAL_L, TERMINAL_W, TERMINAL_H, (0.85, 0.75, 0.10),
    )

    add_standoffs(
        doc, "RaspberryPi", RASPI_X, RASPI_Y, RASPI_L, RASPI_W,
        ((3.5, 3.5), (3.5, RASPI_W - 3.5), (RASPI_L - 3.5, 3.5),
         (RASPI_L - 3.5, RASPI_W - 3.5)),
    )
    add_standoffs(
        doc, "ESP32", ESP32_X, ESP32_Y, ESP32_L, ESP32_W,
        ((3.0, 3.0), (3.0, ESP32_W - 3.0),
         (ESP32_L - 3.0, 3.0), (ESP32_L - 3.0, ESP32_W - 3.0)),
    )

    for obj in (raspberry, esp32, psu, terminal):
        obj.addProperty("App::PropertyString", "Purpose", "Documentation")
        obj.Purpose = "Clearance envelope only; replace with measured geometry"

    doc.recompute()
    doc.saveAs("AmpDetc_Enclosure.FCStd")
    if "Gui" in globals():
        Gui.activeDocument().activeView().viewAxonometric()
        Gui.activeDocument().activeView().fitAll()
    return doc


create_model()
