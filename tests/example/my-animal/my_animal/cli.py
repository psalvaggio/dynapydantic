import click

@click.group()
def cli() -> None:
    """Demo CLI"""

@cli.command()
def list() -> None:
    from . import Animal

    print(Animal.registered_subclasses())

@cli.command()
@click.argument("animal_json", type=str)
def parse(animal_json: str) -> None:
    import pydantic
    from . import Animal

    class Parse(pydantic.RootModel):
        root: Animal.union()

    parsed = Parse.model_validate_json(animal_json).root
    dumped = parsed.model_dump_json()
    reparsed = Parse.model_validate_json(dumped).root
    print(reparsed)
    reparsed.speak()
