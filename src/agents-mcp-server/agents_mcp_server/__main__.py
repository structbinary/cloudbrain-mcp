import click

from agents_mcp_server.server import main as server_main


@click.command()
@click.option(
    '--host',
    'host',
    default='localhost',
    help='Host on which the server is started or the client connects to',
)
@click.option(
    '--port',
    'port',
    default=8080,
    help='Port on which the server is started or the client connects to',
)
@click.option(
    '--transport',
    'transport',
    default='sse',
    help='MCP Transport',
)
def main(host, port, transport) -> None:
    server_main(host, port, transport)

if __name__ == '__main__':
    main()
