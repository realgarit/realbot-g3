## 2025-02-13 - [Improving Treeview Keyboard Accessibility]
**Learning:** In Tkinter/ttkbootstrap applications with global key bindings, widgets like Treeview can have their standard keyboard navigation broken if not properly managed. Overriding arrow keys to force focus elsewhere is a common but disruptive pattern that kills accessibility.
**Action:** Always prefer semantic events like `<<TreeviewSelect>>` over mouse-specific ones, and use FocusIn/FocusOut to manage global hotkey states instead of hijacking navigation keys.
