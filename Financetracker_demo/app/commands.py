import click
from flask.cli import with_appcontext

from app.extensions import db


@click.command("init-db")
@with_appcontext
def init_db_command():
    import app.models

    db.create_all()
    click.echo("Database tables created.")


@click.command("reset-db")
@click.confirmation_option(prompt="This deletes ALL data. Continue?")
@with_appcontext
def reset_db_command():
    import app.models

    db.drop_all()
    db.create_all()
    click.echo("Database reset.")


def register_commands(app):
    app.cli.add_command(init_db_command)
    app.cli.add_command(reset_db_command)
