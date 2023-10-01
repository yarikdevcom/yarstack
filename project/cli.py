import click
import uvicorn

import project


@click.command()
@click.option('--reload', default=False, help='Port of the server')
@click.option('--port', default=8000, help='Port of the server')
@click.option('--host', default='0.0.0.0', help='Host of the server')
def server(host, port, reload):
    app = 'project:asgi_app' if reload else project.asgi_app
    uvicorn.run(app, host=host, port=port, reload=reload, log_level="info")


@click.command()
@click.option('--port', default=3500, help='Port of the server')
@click.option('--host', default='0.0.0.0', help='Host of the server')
@click.pass_context
def dev_server(ctx, host, port):
    ctx.invoke(server, host=host, port=port, reload=True)