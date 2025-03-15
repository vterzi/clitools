"""Classes for drawing."""

__all__ = ["ScreenBuffer", "KeyHandler", "Anchor", "Drawable", "Rectangle"]

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
        return getch().decode()

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
        return stdin.read(1)


class KeyHandler(ABC):
    """Handler for keypresses."""

    @abstractmethod
    def handle(self, key: str) -> None:
        """Handle a keypress."""


class ScreenBuffer:
    """Alternative screen buffer."""

    def __init__(self) -> None:
        self._cols = 0
        self._rows = 0
        self._buffer: "list[str]" = []
        self.cursor_col = 1
        self.cursor_row = 1
        self._objects: "list[Drawable]" = []
        self._handlers: "set[KeyHandler]" = set()

        def resize_handler(signum: int, frame: "FrameType|None") -> None:
            size = get_terminal_size()
            cols = size.columns
            rows = size.lines
            self._cols = cols
            self._rows = rows
            self._buffer = [" "] * (cols * rows)
            self.cursor_col = min(self.cursor_col, cols)
            self.cursor_row = min(self.cursor_row, rows)
            self.draw()

        self._stdin_attrs = get_stdin_attrs()
        set_stdin_raw()
        print("\033[?1049h")
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

    def idx(self, row: int, col: int) -> int:
        """Get the buffer index for a one-based position (row, column)."""
        cols = self._cols
        rows = self._rows
        return (
            col - 1 + (row - 1) * cols
            if 1 <= col <= cols and 1 <= row <= rows
            else -1
        )

    def __getitem__(self, key: "tuple[int, int]") -> str:
        idx = self.idx(key[0], key[1])
        return self._buffer[idx] if idx >= 0 else ""

    def __setitem__(self, key: "tuple[int, int]", value: str) -> None:
        idx = self.idx(key[0], key[1])
        if idx >= 0:
            self._buffer[idx] = value[0]

    def show_cursor(self) -> None:
        """Show the cursor's current position."""
        print(f"\033[{self.cursor_row};{self.cursor_col}H", end="", flush=True)

    def add(self, obj: "Drawable") -> None:
        """Add a drawable object."""
        self._objects.append(obj)
        self.draw()

    def remove(self, obj: "Drawable") -> None:
        """Remove a drawable object."""
        self._objects.remove(obj)
        self.draw()

    def clear(self) -> None:
        """Clear the buffer."""
        buffer = self._buffer
        for i in range(len(buffer)):
            buffer[i] = " "

    def draw(self) -> None:
        """Draw the buffer."""
        self.clear()
        for obj in self._objects:
            obj.draw(self)
        print("\033[H" + "".join(self._buffer), end="", flush=True)
        self.show_cursor()

    def listen_keys(self) -> None:
        """Listen for input."""
        handlers = self._handlers
        while True:
            key = get_key()
            if key == "q":
                break
            if key == "\033":
                if get_key() == "[":
                    key = get_key()
                    if key == "A" and self.cursor_row > 1:
                        self.cursor_row -= 1
                    elif key == "B" and self.cursor_row < self._rows:
                        self.cursor_row += 1
                    elif key == "C" and self.cursor_col < self._cols:
                        self.cursor_col += 1
                    elif key == "D" and self.cursor_col > 1:
                        self.cursor_col -= 1
                self.show_cursor()
            else:
                for handler in handlers:
                    handler.handle(key)

    def close(self) -> None:
        """Close frame."""
        print("\033[?1049l")
        set_stdin_attrs(self._stdin_attrs)


class Anchor:
    """Anchor."""

    def __init__(self, y: float, x: float) -> None:
        self.x = x
        self.y = y

    def col(self, cols) -> int:
        """Get the column index."""
        return self.x * (cols - 1) + 1

    def row(self, rows) -> int:
        """Get the row index."""
        return self.y * (rows - 1) + 1


class Drawable(ABC):
    """Drawable object."""

    @abstractmethod
    def draw(self, frame: ScreenBuffer) -> None:
        """Draw object."""


class Rectangle(Drawable):
    """Rectangle."""

    def __init__(self, top_left: Anchor, bottom_right: Anchor) -> None:
        self.top_left = top_left
        self.bottom_right = bottom_right

    def draw(self, frame: ScreenBuffer) -> None:
        cols = frame.cols
        rows = frame.rows
        x = self.top_left.col(cols)
        y = self.top_left.row(rows)
        w = self.bottom_right.col(cols) - x + 1
        h = self.bottom_right.row(rows) - y + 1
        frame[y, x] = "╔"
        for i in range(1, w - 1):
            frame[y, x + i] = "═"
        frame[y, x + w - 1] = "╗"
        for j in range(1, h - 1):
            frame[y + j, x] = "║"
            frame[y + j, x + w - 1] = "║"
        frame[y + h - 1, x] = "╚"
        for i in range(1, w - 1):
            frame[y + h - 1, x + i] = "═"
        frame[y + h - 1, x + w - 1] = "╝"
