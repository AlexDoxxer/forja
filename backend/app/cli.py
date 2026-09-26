"""CLI operativa del backend: ``create-admin`` y ``seed-demo`` (solo desarrollo)."""

import asyncio
from typing import Annotated

import typer
from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import create_engine, create_sessionmaker
from app.models.user import Profile, User
from app.security import passwords
from app.services.auth import default_profile

app = typer.Typer(help="Operaciones del backend de Forja.", no_args_is_help=True)

DEMO_EMAIL = "demo@forja.local"
DEMO_PASSWORD = "brasa-y-yunque-2026"  # noqa: S105 - usuario de demostración, solo desarrollo


async def _create_user(email: str, password: str, name: str, role: str) -> str:
    engine = create_engine(get_settings())
    factory = create_sessionmaker(engine)
    try:
        async with factory() as db:
            existing = (
                await db.execute(select(User).where(User.email == email))
            ).scalar_one_or_none()
            if existing is not None:
                return "exists"
            user = User(
                email=email,
                password_hash=await passwords.hash_password_async(password),
                display_name=name,
                role=role,
            )
            db.add(user)
            await db.flush()
            profile: Profile = default_profile(user.id)
            db.add(profile)
            await db.commit()
            return "created"
    finally:
        await engine.dispose()


@app.command("create-admin")
def create_admin(
    email: Annotated[str, typer.Option(prompt=True)],
    password: Annotated[str, typer.Option(prompt=True, hide_input=True, confirmation_prompt=True)],
    name: Annotated[str, typer.Option()] = "Admin",
) -> None:
    """Crea un administrador (bootstrap con el registro cerrado)."""
    if len(password) < passwords.MIN_PASSWORD_LENGTH or passwords.is_weak_password(password, email):
        typer.echo("Contraseña demasiado corta o común.")
        raise typer.Exit(1)
    typer.echo(asyncio.run(_create_user(email, password, name, "admin")))


@app.command("seed-demo")
def seed_demo() -> None:
    """Crea el usuario ``demo@forja.local`` (solo desarrollo)."""
    typer.echo(asyncio.run(_create_user(DEMO_EMAIL, DEMO_PASSWORD, "Demo", "user")))
    typer.echo(f"usuario: {DEMO_EMAIL} · contraseña: {DEMO_PASSWORD}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
