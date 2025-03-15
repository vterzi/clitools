"""Server."""

from sys import argv

from clitools.connect import read_port, Server


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

    host = "0.0.0.0"
    try:
        server = Server((host, port))
    except OSError as err:
        print(f"{err} ({host}:{port})")
        return

    try:
        server.accept()
    except KeyboardInterrupt:
        pass
    finally:
        server.close()


if __name__ == "__main__":
    main()
