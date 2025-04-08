"""
Entrypoint for TOOL_NAME CLI

Check out the wiki for a detailed look at customizing this file:
https://github.com/beardymcjohnface/Snaketool/wiki/Customising-your-Snaketool
"""

import os
import click
from .util import (
    snake_base,
    run_snakemake,
    get_version,
    copy_config,
    OrderedCommands,
    print_citation,
)


def common_options(func):
    """Common options decorator for use with click commands."""
    options = [
        click.argument("nextflow_args", nargs=-1),
    ]
    for option in reversed(options):
        func = option(func)
    return func


@click.group(
    cls=OrderedCommands, context_settings=dict(help_option_names=["-h", "--help"])
)
@click.version_option(get_version(), "-v", "--version", is_flag=True)
@click.option(
    "--citation",
    is_flag=True,
    callback=print_citation,
    expose_value=False,
    is_eager=True,
    help="Print the citation in bibtex format and exit.",
)
def cli():
    """TODO oneline description of TOOL_NAME

    For more options, run:
    tool_name [command] --help"""
    pass


help_msg_extra = """
\b
EXAMPLES:
Execute with slurm:
    tool_name run ... --mode slurm
Preview the processes that will run:
    tool_name run ... --mode local -preview
Add nextflow args (anything supported by `nextflow run`):
    tool_name run ... -work-dir path/to/workDir
Run with a specific installation of tool_name:
    tool_name run --main path/to/tool_name/main.nf ...
Run with a specific tag, branch, or commit from GitHub:
    tool_name run --main CCBR/TOOL_NAME -r v0.1.0 ...
"""


@click.command(
    epilog=help_msg_extra,
    context_settings=dict(
        help_option_names=["-h", "--help"], ignore_unknown_options=True
    ),
)
@click.option(
    "--main",
    "main_path",
    help="Path to the tool_name Snakefile. Defaults to the version installed in the $PATH.",
    type=str,
    default=snake_base(os.path.join("workflow", "Snakefile")),
    show_default=True,
)
@click.option(
    "--mode",
    "_mode",
    help="Run mode (slurm, local)",
    type=str,
    default="local",
    show_default=True,
)
@common_options
def run(main_path, _mode, **kwargs):
    """Run the workflow"""
    if (  # this is the only acceptable github repo option for tool_name
        main_path != "CCBR/TOOL_NAME"
    ):
        # make sure the path exists
        if not os.path.exists(main_path):
            raise FileNotFoundError(
                f"Path to the tool_name main.nf file not found: {main_path}"
            )

    run_snakemake(
        snakefile_path=main_path,
        mode=_mode,
        **kwargs,
    )


@click.command()
def init(**kwargs):
    """Initialize the working directory by copying the system default config files"""
    paths = ("nextflow.config", "config/", "assets/")
    copy_config(paths)
    if not os.path.exists("log/"):
        os.mkdir("log/")


cli.add_command(run)
cli.add_command(init)


def main():
    cli()


cli(prog_name="tool_name")

if __name__ == "__main__":
    main()
