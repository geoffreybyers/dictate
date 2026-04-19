import pytest
from dictate.hotkey import parse_binding, HotkeyState, Mode


def test_parse_binding_simple_key():
    keys = parse_binding("F9")
    assert keys == frozenset({"f9"})


def test_parse_binding_modifier_combo():
    keys = parse_binding("ctrl+shift+d")
    assert keys == frozenset({"ctrl", "shift", "d"})


def test_parse_binding_case_insensitive():
    assert parse_binding("Ctrl+Shift+D") == parse_binding("ctrl+shift+d")


def test_parse_binding_space_requires_modifier():
    with pytest.raises(ValueError):
        parse_binding("space")
    # with a modifier is fine
    assert parse_binding("ctrl+space") == frozenset({"ctrl", "space"})


def test_hold_mode_press_starts_release_stops():
    started = []
    stopped = []
    hs = HotkeyState(Mode.HOLD, on_start=lambda: started.append(1),
                                 on_stop=lambda: stopped.append(1))
    hs.on_combo_press()
    assert started == [1]
    assert stopped == []
    hs.on_combo_release()
    assert stopped == [1]


def test_hold_mode_double_press_no_double_start():
    started = []
    hs = HotkeyState(Mode.HOLD, on_start=lambda: started.append(1),
                                 on_stop=lambda: None)
    hs.on_combo_press()
    hs.on_combo_press()
    assert started == [1]


def test_toggle_mode_press_flips_state():
    started = []
    stopped = []
    hs = HotkeyState(Mode.TOGGLE, on_start=lambda: started.append(1),
                                   on_stop=lambda: stopped.append(1))
    hs.on_combo_press()
    assert started == [1] and stopped == []
    hs.on_combo_release()  # release is ignored in toggle mode
    assert stopped == []
    hs.on_combo_press()
    assert stopped == [1]


def test_external_toggle_works_regardless_of_mode():
    started = []
    stopped = []
    hs = HotkeyState(Mode.HOLD, on_start=lambda: started.append(1),
                                 on_stop=lambda: stopped.append(1))
    hs.external_toggle()
    assert started == [1]
    hs.external_toggle()
    assert stopped == [1]
