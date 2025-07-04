import click
from .base import DynamicBaseModel
from .registry import load_plugins

@click.group()
def cli():
    pass

@cli.command()
@click.argument("base")
def list(base):
    load_plugins()
    cls = globals().get(base)
    if cls and issubclass(cls, DynamicBaseModel):
        for k in cls.list_registered():
            click.echo(k)
    else:
        click.echo(f"Unknown or invalid base model: {base}")

if __name__ == "__main__":
    cli()
