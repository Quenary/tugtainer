#!/usr/bin/env python3
"""Forward localhost registry ports to compose services.

The Docker daemon pulls ``localhost:5000`` from the published host port.
Inside the app container, localhost is not the host, so digest checks of
those image names need this forwarder. The test stack starts it; the
product image does not.
"""

import socket
import threading

FORWARDS = (
    (5000, "registry", 5000),
    (5001, "private-registry", 5000),
    (5002, "unauthorized-registry", 5000),
)


def _pipe(src: socket.socket, dst: socket.socket) -> None:
    try:
        while True:
            data = src.recv(65536)
            if not data:
                break
            dst.sendall(data)
    except OSError:
        pass
    finally:
        try:
            dst.shutdown(socket.SHUT_WR)
        except OSError:
            pass


def _handle(client: socket.socket, host: str, port: int) -> None:
    try:
        remote = socket.create_connection((host, port), timeout=10)
    except OSError:
        client.close()
        return
    client_to_remote = threading.Thread(
        target=_pipe, args=(client, remote), daemon=True
    )
    remote_to_client = threading.Thread(
        target=_pipe, args=(remote, client), daemon=True
    )
    client_to_remote.start()
    remote_to_client.start()
    client_to_remote.join()
    remote_to_client.join()
    for sock in (client, remote):
        try:
            sock.close()
        except OSError:
            pass


def _serve(listen_port: int, host: str, port: int) -> None:
    server = socket.socket()
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", listen_port))
    server.listen()
    while True:
        client, _addr = server.accept()
        threading.Thread(target=_handle, args=(client, host, port), daemon=True).start()


def main() -> None:
    for listen_port, host, port in FORWARDS:
        threading.Thread(
            target=_serve, args=(listen_port, host, port), daemon=True
        ).start()
    threading.Event().wait()


if __name__ == "__main__":
    main()
