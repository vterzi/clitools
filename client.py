"""Client."""

from sys import argv

from clitools.draw import ScreenBuffer, Anchor, Rectangle
from clitools.connect import read_port, ServerConnection


def main() -> None:
    """Main procedure."""
    if len(argv) - 1 != 1:
        print(f"usage: python {__file__.rsplit('/', maxsplit=1)[-1]} <port>")
        return
    try:
        port = read_port(argv[1])
    except ValueError as err:
        print(err)
        return

    host = "localhost"
    try:
        server = ServerConnection((host, port))
    except ConnectionRefusedError as err:
        print(err)
        return

    frame = ScreenBuffer()
    frame.add(Rectangle(Anchor(0, 0), Anchor(1, 1)))

    try:
        frame.listen_keys()
    finally:
        frame.close()
        server.close()


if __name__ == "__main__":
    main()
