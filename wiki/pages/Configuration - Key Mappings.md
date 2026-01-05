🏠 [`realbot-g3` Wiki Home](../README.md)

# 🎮 Key Mappings

You can control the emulator with your keyboard. If you want to change these keys, you can edit [`profiles/keys.yml`](../../modules/config/templates/keys.yml).

## GBA Buttons

- **Arrow Keys** = D-pad
- **A** = A button
- **S** = B button
- **Q** = L button
- **W** = R button
- **Enter** = Start
- **Backspace** = Select

## Emulator Keys

- **Plus (+)** and **Minus (-)** keys change the zoom level.
- **V** = Turn video on or off.
- **B** = Turn sound on or off.
- **0** = Run the game as fast as possible.
- **1 through 7** = Set the speed (1x up to 32x).
- **Ctrl + R** = Reset the game (like turning it off and on).
- **Ctrl + L** = Open a window to load a save state.
- **F12** = Take a screenshot. It'll save to your profile's `screenshots/` folder.

## Bot Keys

- **Tab** = Switch between playing manually and letting the bot take over.
- **Ctrl + C** = Reload your settings.
## Valid Key Names

The bot uses standard **Tcl/Tk** key names. If you want to use a key that isn't listed above, you can find the correct name to use in these references:
- [Official Tcl/Tk Keysym List](https://www.tcl.tk/man/tcl8.4/TkCmd/keysyms.html)
- [Tkinter Key Names Guide](https://anzeljg.github.io/rin2/book2/2405/docs/tkinter/key-names.html) (use the names in the `.keysym` column)
