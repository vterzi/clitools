"""Classes for drawing."""

__all__ = ["Screen", "Point", "Displayable", "Text", "Button", "Rectangle"]

from abc import ABC, abstractmethod
from sys import platform, stdin
from shutil import get_terminal_size
from signal import signal, SIGWINCH
from types import FrameType

if platform == "win32":
    from msvcrt import getch  # type: ignore

    def get_stdin_attrs() -> list:
        """Get the TTY attributes of the stdandard input."""
        return []

    def set_stdin_attrs(attrs: list) -> None:
        """Set the TTY attributes of the stdandard input."""
        pass

    def set_stdin_raw() -> None:
        """Set the mode of the stdandard input to raw."""
        pass

    def get_key() -> str:
        """Read a keypress."""
        key = getch()
        if key in {b"\x00", b"\xe0"}:
            key += getch()
        return key.decode(errors="ignore")

else:
    from tty import setraw
    from termios import tcgetattr, tcsetattr, TCSADRAIN

    def get_stdin_attrs() -> list:
        """Get the TTY attributes of the stdandard input."""
        return tcgetattr(stdin)

    def set_stdin_attrs(attrs: list) -> None:
        """Set the TTY attributes of the stdandard input."""
        tcsetattr(stdin, TCSADRAIN, attrs)

    def set_stdin_raw() -> None:
        """Set the mode of the stdandard input to raw."""
        setraw(stdin)

    def get_key() -> str:
        """Read a keypress."""
        key = stdin.read(1)
        if key == "\x1b":
            char = stdin.read(1)
            key += char
            if char in {"[", "O"}:
                while True:
                    char = stdin.read(1)
                    key += char
                    if char.isalpha() or char == "~":
                        # if char == "M":
                        #     key += stdin.buffer.read(3).decode(
                        #         errors="ignore",
                        #     )
                        break
        return key


class Screen:
    """Alternative screen buffer."""

    @classmethod
    def _print(cls, text: str) -> None:
        """Print text."""
        print(text, end="", flush=True)

    def __init__(self) -> None:
        self._cols = 0
        self._rows = 0
        self._buffer: "list[str]" = []
        self._objects: "list[Displayable]" = []
        self._buttons: "list[Button]" = []
        self._focus: "Button|None" = None

        def resize_handler(signum: int, frame: "FrameType|None") -> None:
            size = get_terminal_size()
            cols = size.columns
            rows = size.lines
            self._cols = cols
            self._rows = rows
            self._buffer = [" "] * (cols * rows)
            self.display()

        self._stdin_attrs = get_stdin_attrs()
        set_stdin_raw()
        self._print("\x1b[?1049h\x1b[?25l\x1b[?1003h\x1b[?1006h")
        resize_handler(int(SIGWINCH), None)
        signal(SIGWINCH, resize_handler)

    @property
    def cols(self) -> int:
        """Number of columns."""
        return self._cols

    @property
    def rows(self) -> int:
        """Number of rows."""
        return self._rows

    def _idx(self, row: int, col: int) -> int:
        """Get the buffer index for a one-based position (row, column)."""
        cols = self._cols
        rows = self._rows
        return (
            col - 1 + (row - 1) * cols
            if 1 <= col <= cols and 1 <= row <= rows
            else -1
        )

    def __getitem__(self, key: "tuple[int, int]") -> str:
        idx = self._idx(key[0], key[1])
        return self._buffer[idx] if idx >= 0 else ""

    def __setitem__(self, key: "tuple[int, int]", value: str) -> None:
        idx = self._idx(key[0], key[1])
        if idx >= 0:
            self._buffer[idx] = value[0]

    def add(self, obj: "Displayable") -> None:
        """Add a displayable object."""
        self._objects.append(obj)
        if isinstance(obj, Button):
            self._buttons.append(obj)
        self.display()

    def remove(self, obj: "Displayable") -> None:
        """Remove a displayable object."""
        self._objects.remove(obj)
        if isinstance(obj, Button):
            self._buttons.remove(obj)
        self.display()

    def fmt(self, fmt: str, row: int, col: int, width: int) -> None:
        """Select graphic rendition for a part of the buffer."""
        if 1 <= row <= self._rows:
            cols = self._cols
            col = min(max(1, col), cols)
            width = min(max(1, width), cols - col + 1)
            idx = self._idx(row, col)
            self._buffer[idx] = f"\x1b[{fmt}m" + self._buffer[idx]
            idx += width - 1
            self._buffer[idx] = self._buffer[idx] + "\x1b[m"

    def clear(self) -> None:
        """Clear the buffer."""
        buffer = self._buffer
        for i in range(len(buffer)):
            buffer[i] = " "

    def display(self) -> None:
        """Display the buffer."""
        self.clear()
        for obj in self._objects:
            obj.display()
        if self._focus is not None:
            self._focus.focus()
        self._print("\x1b[H" + "".join(self._buffer))

    def listen_keys(self) -> None:
        """Listen for input."""
        buttons = self._buttons
        while True:
            key = get_key()
            if key == "\x1b\x1b":
                break
            if key in {"\x1b[A", "\x1b[B", "\x1b[C", "\x1b[D"}:
                if self._focus is not None:
                    focus = self._focus
                    center = focus.center
                    col = center[1]
                    row = center[0]
                    if key == "\x1b[A":
                        col_factor = 0
                        row_factor = -1
                    elif key == "\x1b[B":
                        col_factor = 0
                        row_factor = 1
                    elif key == "\x1b[C":
                        col_factor = 1
                        row_factor = 0
                    elif key == "\x1b[D":
                        col_factor = -1
                        row_factor = 0
                    best_weight = 0.0
                    choice = -1
                    for i, button in enumerate(buttons):
                        if button != focus:
                            center = button.center
                            col_diff = center[1] - col
                            row_diff = 2 * (center[0] - row)
                            weight = (
                                col_factor * col_diff + row_factor * row_diff
                            ) / (col_diff * col_diff + row_diff * row_diff + 1)
                            if weight > best_weight:
                                best_weight = weight
                                choice = i
                    if choice >= 0:
                        self._focus = buttons[choice]
                elif len(buttons) > 0:
                    self._focus = buttons[0]
                self.display()
            elif key == "\r" and self._focus is not None:
                self._focus.press()

    def close(self) -> None:
        """Close the buffer."""
        self._print("\x1b[?1049l\x1b[?25h\x1b[?1003l\x1b[?1006l")
        set_stdin_attrs(self._stdin_attrs)


class Point:
    """Point in normalized coordinates."""

    def __init__(self, y: float, x: float) -> None:
        self.x = x
        self.y = y

    def col(self, cols) -> int:
        """Get the column index."""
        return self.x * (cols - 1) + 1

    def row(self, rows) -> int:
        """Get the row index."""
        return self.y * (rows - 1) + 1


class Displayable(ABC):
    """Displayable object."""

    def __init__(self, screen: Screen) -> None:
        self._screen = screen
        screen.add(self)

    @abstractmethod
    def display(self) -> None:
        """Display the object."""


class Text(Displayable):
    """Text."""

    def __init__(
        self,
        screen: Screen,
        text: str,
        row: int,
        col: int,
        fmt: str = "",
    ) -> None:
        self._text = text
        self.col = col
        self.row = row
        self._fmt = fmt
        super().__init__(screen)

    def display(self) -> None:
        screen = self._screen
        col = self.col
        row = self.row
        text = self._text
        for i, char in enumerate(text):
            screen[row, col + i] = char
        fmt = self._fmt
        if fmt:
            screen.fmt(fmt, row, col, len(text))


class Button(Text):
    """Button."""

    @property
    def center(self) -> "tuple[int, int]":
        """Get the position of the center."""
        return self.row, self.col + (len(self._text) - 1) // 2

    def focus(self) -> None:
        """Focus on the button."""
        self._screen.fmt("7", self.row, self.col, len(self._text))

    def press(self) -> None:
        """Press the button."""


class Rectangle(Displayable):
    """Rectangle."""

    def __init__(
        self, screen: Screen, top_left: Point, bottom_right: Point
    ) -> None:
        self.top_left = top_left
        self.bottom_right = bottom_right
        super().__init__(screen)

    def display(self) -> None:
        screen = self._screen
        cols = screen.cols
        rows = screen.rows
        top_left = self.top_left
        x = top_left.col(cols)
        y = top_left.row(rows)
        bottom_right = self.bottom_right
        w = bottom_right.col(cols) - x + 1
        h = bottom_right.row(rows) - y + 1
        screen[y, x] = "╔"
        for i in range(1, w - 1):
            screen[y, x + i] = "═"
        screen[y, x + w - 1] = "╗"
        for j in range(1, h - 1):
            screen[y + j, x] = "║"
            screen[y + j, x + w - 1] = "║"
        screen[y + h - 1, x] = "╚"
        for i in range(1, w - 1):
            screen[y + h - 1, x + i] = "═"
        screen[y + h - 1, x + w - 1] = "╝"
