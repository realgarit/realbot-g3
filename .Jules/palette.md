## 2025-02-13 - [Improving Treeview Keyboard Accessibility]
**Learning:** In Tkinter/ttkbootstrap applications with global key bindings, widgets like Treeview can have their standard keyboard navigation broken if not properly managed. Overriding arrow keys to force focus elsewhere is a common but disruptive pattern that kills accessibility.
**Action:** Always prefer semantic events like `<<TreeviewSelect>>` over mouse-specific ones, and use FocusIn/FocusOut to manage global hotkey states instead of hijacking navigation keys.

## 2026-05-20 - [Discoverability for Icon-Only Buttons]
**Learning:** In complex control panels with many buttons, icons and minimal text (like "∞" or "⮞") can be ambiguous. Tooltips provide essential context without cluttering the UI, and are a great place to document keyboard shortcuts.
**Action:** Use `ttkbootstrap.tooltip.ToolTip` for all interactive elements that lack clear descriptive text, and include keyboard shortcut hints in parentheses.

## 2025-02-13 - [Enhancing Discoverability with Tooltips]
**Learning:** In applications with icon-only or text-minimal buttons (like "∞", "…", or "+"), users may struggle to identify their functions quickly. Tooltips provide a non-intrusive way to offer guidance without cluttering the interface.
**Action:** Use `ttkbootstrap.tooltip.ToolTip` for any interactive element whose purpose isn't immediately obvious from its label or icon alone.
