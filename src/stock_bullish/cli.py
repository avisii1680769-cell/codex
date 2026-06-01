from pathlib import Path

import typer
from rich.console import Console

from stock_bullish import __version__
from stock_bullish.research import run_research
from stock_bullish.web import serve

app = typer.Typer()
console = Console()


@app.command()
def version() -> None:
    console.print(__version__)


@app.command()
def research(
    input_path: Path,
    output_dir: Path = Path("outputs/research"),
    strategy_name: str = "all",
) -> None:
    try:
        output = run_research(input_path=input_path, output_dir=output_dir, strategy_name=strategy_name)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--strategy-name") from exc
    console.print(f"Wrote reports: {output.paths}")


@app.command()
def web(
    host: str = "127.0.0.1",
    port: int = 8765,
    output_dir: Path = Path("outputs/web"),
) -> None:
    serve(host=host, port=port, output_dir=output_dir)
