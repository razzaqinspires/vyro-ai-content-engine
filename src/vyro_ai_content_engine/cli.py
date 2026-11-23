from pathlib import Path
import json
import typer
from rich import print
from .engine import ContentEngine
from .models import ContentBrief

app = typer.Typer(no_args_is_help=True, help="VYRO AI Content Engine — text and storyboard only")

@app.command()
def validate(source: Path = typer.Argument(..., exists=True, readable=True)):
    brief = ContentBrief.model_validate_json(source.read_text(encoding="utf-8"))
    print(f"[green]Valid brief:[/green] {brief.content_id} — {brief.title}")

@app.command()
def generate(source: Path = typer.Argument(..., exists=True, readable=True),
             output: Path = typer.Option(..., "--output", "-o")):
    brief = ContentBrief.model_validate_json(source.read_text(encoding="utf-8"))
    package = ContentEngine.from_env().generate(brief)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(package.model_dump_json(indent=2), encoding="utf-8")
    print(f"[green]Content package ready:[/green] {output}")
    print("[yellow]Human review required. Audio synthesis is handled by vyro-ai-voice-studio.[/yellow]")

if __name__ == "__main__":
    app()
