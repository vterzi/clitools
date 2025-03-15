"""Classes for server and client communication."""

__all__ = [
    "read_port",
    "Server",
    "MessageHandler",
    "ClientConnection",
    "ServerConnection",
]

from abc import ABC, abstractmethod
from socket import socket, AF_INET, SOCK_STREAM
from threading import Thread

BUF_SIZE = 1024


def read_port(arg: str) -> int:
    """Read a port from a string."""
    if not arg.isdigit():
        raise ValueError("unsigned integer number for port expected")
    port = int(arg)
    if not 1 << 10 <= port < 1 << 16:
        raise ValueError("port in 1024..65535 expected")
    return port


class Logger(ABC):
    """Logger."""

    @abstractmethod
    def log(self, msg: str) -> None:
        """Log a message."""


class NullLogger(Logger):
    """Null logger."""

    def log(self, msg: str) -> None:
        pass


class StdoutLogger(Logger):
    """Standard output logger."""

    def __init__(self, prefix: str = "") -> None:
        self._prefix = prefix

    def log(self, msg: str) -> None:
        print(self._prefix + msg)


class Server:
    """Server."""

    def __init__(self, addr: "tuple[str, int]") -> None:
        conn = socket(AF_INET, SOCK_STREAM)
        self._conn = conn
        self._addr = addr
        self._clients: "set[ClientConnection]" = set()
        self._logger: Logger = StdoutLogger("[SERVER] ")
        conn.bind(addr)
        conn.listen()
        self._logger.log(f"listening on {addr[0]}:{addr[1]}")

    def accept(self) -> None:
        """Accept client connections."""
        conn = self._conn
        while True:
            self._clients.add(ClientConnection(*conn.accept(), self))

    def remove(self, client: "ClientConnection") -> None:
        """Remove a client."""
        self._clients.discard(client)

    def bcast(self, msg: str) -> None:
        """Broadcast a message to all clients."""
        disconn: "set[ClientConnection]" = set()
        for client in self._clients:
            try:
                client.send(msg)
            except ConnectionResetError:
                disconn.add(client)
        for client in disconn:
            self.remove(client)

    def close(self) -> None:
        """Close server connection."""
        self._conn.close()
        self._logger.log("shutting down")


class MessageHandler(ABC):
    """Handler for messages."""

    @abstractmethod
    def handle(self, msg: str) -> None:
        """Handle a message."""


class Connection:
    """Connection."""

    def __init__(self, conn: socket, logger: Logger = NullLogger()) -> None:
        self._conn = conn
        self._logger = logger
        self._handlers: "set[MessageHandler]" = set()
        thread = Thread(target=self.recv, daemon=True)
        thread.start()

    def add_handler(self, handler: MessageHandler) -> None:
        """Add a handler for recieved messages."""
        self._handlers.add(handler)

    def remove_handler(self, handler: MessageHandler) -> None:
        """Remove a handler for recieved messages."""
        self._handlers.discard(handler)

    def send(self, msg: str) -> None:
        """Send a message."""
        logger = self._logger
        try:
            self._conn.sendall(msg.encode())  # BrokenPipeError
            logger.log("sent message: " + msg)
        except BrokenPipeError:
            logger.log("broken pipe")
            self.close()

    def recv(self) -> None:
        """Recieve messages."""
        conn = self._conn
        handlers = self._handlers
        logger = self._logger
        logger.log("connected")
        try:
            while True:
                data = conn.recv(BUF_SIZE)  # ConnectionResetError
                if not data:
                    break
                msg = data.decode().strip()
                logger.log("recieved message: " + msg)
                for handler in handlers:
                    handler.handle(msg)
        except ConnectionResetError:
            logger.log("connection reset")
        finally:
            logger.log("disconnected")
            self.close()

    def close(self) -> None:
        """Close the connection."""
        self._conn.close()


class ClientConnection(Connection):
    """Connection with a client."""

    def __init__(
        self, conn: socket, addr: "tuple[str, int]", server: Server
    ) -> None:
        self._addr = addr
        self._server = server
        super().__init__(conn, StdoutLogger(f"[CLIENT({addr[0]}:{addr[1]})] "))

    def close(self) -> None:
        super().close()
        self._server.remove(self)


class ServerConnection(Connection):
    """Connection with a server."""

    def __init__(self, addr: "tuple[str, int]") -> None:
        self._addr = addr
        conn = socket(AF_INET, SOCK_STREAM)
        conn.connect(addr)  # ConnectionRefusedError
        super().__init__(conn)
