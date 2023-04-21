import typer
from rich import print

from tagclass import __version__
from tagclass.tag import Vocabulary
from tagclass.tokenizer import Tokenizer
from tagclass.common import VOC_FILES, INIT_VOC_FILES
from tagclass.cli.clean import app as clean_app
from tagclass.cli.evaluate import app as evaluate_app
from tagclass.cli.parse import app as parse_app
from tagclass.cli.update import app as update_app
# ================== CLI ===================
app = typer.Typer(add_completion=False)
app.add_typer(
    evaluate_app,
    name="evaluate",
    help="Evaluation for TagClass",
)
app.add_typer(
    clean_app,
    name="clean",
    help="Clean pending vocabulary",
)
app.add_typer(
    parse_app,
    name="parse",
    help="Location first search wrapped parsing",
)
app.add_typer(
    update_app,
    name="update",
    help="Incremental parsing wrapped updating",
)
# ==========================================


@app.command(short_help='TagClass version')
def version():
    print(__version__)


@app.command(short_help='List vocabulary')
def list(init: bool = False):
    if init:
        voc = Vocabulary(INIT_VOC_FILES)
    else:
        voc = Vocabulary(VOC_FILES)
    print(voc)


@app.command(short_help='Tokenizer malware label')
def tokenize(label: str, engine: str = "default"):
    tk = Tokenizer()
    print(tk.run(engine, label))


def main():
    app()