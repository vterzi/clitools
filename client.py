"""Client."""

from sys import argv

from clitools.screen import Screen, Point, Rectangle

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

    try:
        screen = Screen()
        Rectangle(screen, Point(0, 0), Point(1, 1))
        screen.listen_keys()
    finally:
        screen.close()
        server.close()


if __name__ == "__main__":
    main()
