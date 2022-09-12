"""HTTP Session.

Whenever a request comes from the server, a session will be created
based on the request, and a thread will be opened to run the session.
"""
import socket
from typing import Any
from cgiserver.utils import html_file_loader, AttrDict
from cgiserver.router import ROUTER
from cgiserver.logging import get_logger
from cgiserver.http_parser import HttpRequestParser, HttpResponseParser

# pylint: disable = broad-except
try:
    NOFOUND_HTML = html_file_loader("cgiserver/static/404.html")
except Exception:
    NOFOUND_HTML = b"<p> 404 NO FOUND </p>"

logger = get_logger()


class Session:
    """Used to handle an HTTP connection"""

    def __init__(
        self, client_socket: socket.socket, client_address: tuple[str, int]
    ) -> None:
        self.client_socket = client_socket
        self.client_address = client_address

    def __call__(self, *args: Any, **kwds: Any) -> Any:
        parser = HttpRequestParser()
        data = self.client_socket.recv(1024)
        while (config := parser.parse(data)) is None:
            data = self.client_socket.recv(1024)

        try:
            response_html = ROUTER.match(config.url, config.method)()
            if not isinstance(response_html, (str, bytes)):
                response_html = (
                    f"<P> currently does not support {str(type(response_html))[1:-1]} "
                    f"as the return value of the decorated function</P>"
                )
        except Exception:
            response_html = NOFOUND_HTML

        response = HttpResponseParser.make_response(200, config.headers, response_html)
        self._log_current_request(config, self.client_address, 200)

        self.client_socket.send(response)
        self.client_socket.close()

    def run(self, *args: Any, **kwds: Any) -> Any:
        """Run the session, handle an HTTP connection once"""
        # pylint: disable = unnecessary-dunder-call
        return self.__call__(args, kwds)

    def _log_current_request(
        self, config: AttrDict, client_address: tuple[str, int], status_code: int
    ) -> None:
        """log current request.

        Args:
            config (AttrDict): HTTP request config.
            client_address (tuple[str, int]): client address.
            status_code (int): HTPP status code.
        """
        client_ip, client_port = client_address
        method = config.method
        url = config.url
        http_version = config["http-version"]
        user_agent = config.headers["User-Agent"]
        content_length = config.headers["Content-Length"]

        text = f'[{client_ip}:{client_port}] "{method} {url} {http_version}" {status_code} {content_length} "{user_agent}"'
        logger.info(text)
