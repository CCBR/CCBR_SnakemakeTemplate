from cffconvert.cli.create_citation import create_citation
from cffconvert.cli.validate_or_write_output import validate_or_write_output
from time import localtime, strftime

import click
import collections.abc
import os
import shutil
import subprocess
import yaml


def snake_base(rel_path):
    basedir = os.path.split(os.path.dirname(os.path.realpath(__file__)))[0]
    return os.path.join(basedir, rel_path)


def get_version():
    with open(snake_base("VERSION"), "r") as f:
        version = f.readline()
    return version


def print_citation(context, param, value, citation_format="bibtex"):
    if not value or context.resilient_parsing:
        return
    citation = create_citation(snake_base("CITATION.cff"), None)
    # click.echo(citation._implementation.cffobj['message'])
    validate_or_write_output(None, citation_format, False, citation)
    context.exit()


def msg(err_message):
    tstamp = strftime("[%Y:%m:%d %H:%M:%S] ", localtime())
    click.echo(tstamp + err_message, err=True)


def msg_box(splash, errmsg=None):
    msg("-" * (len(splash) + 4))
    msg(f"| {splash} |")
    msg(("-" * (len(splash) + 4)))
    if errmsg:
        click.echo("\n" + errmsg, err=True)


def copy_config(config_paths, overwrite=True):
    msg("Copying default config files to current working directory")
    for local_config in config_paths:
        system_config = snake_base(local_config)
        if os.path.isfile(system_config):
            shutil.copyfile(system_config, local_config)
        elif os.path.isdir(system_config):
            shutil.copytree(system_config, local_config, dirs_exist_ok=overwrite)
        else:
            raise FileNotFoundError(f"Cannot copy {system_config} to {local_config}")


def read_config(file):
    with open(file, "r") as stream:
        _config = yaml.safe_load(stream)
    return _config


def update_config(config, overwrite_config):
    def _update(d, u):
        for key, value in u.items():
            if isinstance(value, collections.abc.Mapping):
                d[key] = _update(d.get(key, {}), value)
            else:
                d[key] = value
        return d

    _update(config, overwrite_config)


def write_config(_config, file):
    msg(f"Writing runtime config file to {file}")
    with open(file, "w") as stream:
        yaml.dump(_config, stream)


class OrderedCommands(click.Group):
    """Preserve the order of subcommands when printing --help"""

    def list_commands(self, ctx: click.Context):
        return list(self.commands)


def scontrol_show():
    scontrol_dict = dict()
    scontrol_out = subprocess.run(
        "scontrol show config", shell=True, capture_output=True, text=True
    ).stdout
    if len(scontrol_out) > 0:
        for line in scontrol_out.split("\n"):
            line_split = line.split("=")
            if len(line_split) > 1:
                scontrol_dict[line_split[0].strip()] = line_split[1].strip()
    return scontrol_dict


def get_hpc():
    scontrol_out = scontrol_show()
    if "ClusterName" in scontrol_out.keys():
        hpc = scontrol_out["ClusterName"]
    else:
        hpc = None
    return hpc


hpc_options = {
    "biowulf": {"profile": "biowulf", "slurm": "assets/slurm_header_biowulf.sh"},
    "fnlcr": {
        "profile": "frce",
        "slurm": "assets/slurm_header_frce.sh",
    },
}


def run_snakemake(
    snakefile_path=None,
    mode="local",
    configfile=None,
    cluster_config=None,
    threads=1,
    snake_default=None,
    snake_args=[],
    profile=None,
    workflow_profile=None,
    system_workflow_profile=None,
    **kwargs,
):
    """Run a Snakefile!

    Args:
        configfile (str): Filepath of config file to pass with --configfile
        snakefile_path (str): Filepath of Snakefile
        threads (int): Number of local threads to request
        snake_default (list): Snakemake args to pass to Snakemake
        snake_args (list): Additional args to pass to Snakemake
        profile (str): Name of Snakemake profile
        workflow_profile (str): Name of Snakemake workflow-profile
        system_workflow_profile (str): Filepath of system workflow-profile config.yaml to copy if not present
        **kwargs:
    """

    snake_command = ["snakemake", "-s", snakefile_path]
    hpc = get_hpc()
    if mode == "slurm" and not hpc:
        raise ValueError("mode is 'slurm' but no HPC environment was detected")

    # add threads
    if "--profile" not in snake_args and profile is None:
        snake_command += ["--cores", threads]

    # add snakemake default args
    if snake_default:
        snake_command += snake_default

    # add any additional snakemake commands
    if snake_args:
        snake_command += list(snake_args)

    # allow double-handling of --profile
    if profile:
        snake_command += ["--profile", profile]

    # allow double-handling of --workflow-profile
    if workflow_profile:
        # copy system default if not present
        copy_config(
            os.path.join(workflow_profile, "config.yaml"),
            system_config=system_workflow_profile,
            log=log,
        )

        snake_command += ["--workflow-profile", workflow_profile]

    # Run Snakemake!!!
    snake_command = " ".join(str(s) for s in snake_command)
    msg_box("Snakemake command", errmsg=snake_command, log=log)
    if mode == "slurm":
        slurm_filename = "submit_slurm.sh"
        with open(slurm_filename, "w") as sbatch_file:
            with open(snake_base(hpc_options[hpc]["slurm"]), "r") as template:
                sbatch_file.writelines(template.readlines())
            sbatch_file.write(snake_command)
        run_command = f"sbatch {slurm_filename}"
        msg_box("Slurm batch job", errmsg=run_command)
    elif mode == "local":
        if hpc:
            snakemake_command = f'bash -c "module load snakemake && {snake_command}"'
        run_command = snakemake_command
    else:
        raise ValueError(f"mode {mode} not recognized")
    # Run snakemake!!!
    subprocess.run(run_command, shell=True, check=True)
