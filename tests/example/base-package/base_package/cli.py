"""CLI to demonstrate usage of dynapydantic"""

import click


@click.group()
def cli() -> None:
    """Demo CLI"""


@cli.group()
def animal() -> None:
    """Animal CLI"""


@animal.command("list")
def list_animal() -> None:
    """List registered animal subclasses"""
    from . import Animal

    click.echo(Animal.registered_subclasses())


@animal.command("parse")
@click.argument("animal_json", type=str)
def parse_animal(animal_json: str) -> None:
    """Parse an animal and ask it to speak"""
    import pydantic

    from . import Animal

    class Parse(pydantic.RootModel):
        root: Animal.union()

    parsed = Parse.model_validate_json(animal_json).root
    dumped = parsed.model_dump_json()
    reparsed = Parse.model_validate_json(dumped).root
    click.echo(reparsed)
    click.echo(reparsed.speak())


@cli.group()
def shape() -> None:
    """Shape CLI"""


@shape.command("list")
def list_shape() -> None:
    """Shape CLI"""
    from . import Shape

    click.echo(Shape.registered_subclasses())


@shape.command("parse")
@click.argument("shape_json", type=str)
def parse_shape(shape_json: str) -> None:
    """Parse a shape and ask it to compute its area"""
    import pydantic

    from . import Shape

    class Parse(pydantic.RootModel):
        root: Shape.union()

    parsed = Parse.model_validate_json(shape_json).root
    dumped = parsed.model_dump_json()
    reparsed = Parse.model_validate_json(dumped).root
    click.echo(reparsed)
    click.echo(f"Area: {reparsed.area()}")
