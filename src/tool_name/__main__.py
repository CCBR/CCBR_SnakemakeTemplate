#!/usr/bin/env python

# Author: Samarth Mathur, PhD
# CCBR, NCI
# (c) 2025
#
# wrapper script to run the snakemake pipeline
# a) on an interactive node (runlocal) OR
# b) submit to the slurm load scheduler (run)
#

# Python standard library
from __future__ import print_function
from shutil import copyfile, copytree
import sys, os, subprocess, re, json, yaml, textwrap, shlex
from pathlib import Path
from datetime import datetime
from rich.console import Console
from .util import get_version

# 3rd party imports from pypi
import argparse  


# Pipeline Metadata and globals
tool_name_path = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
__version__ = get_version()
__home__ = os.path.dirname(os.path.abspath(__file__))
_name = os.path.basename(sys.argv[0])
_description = "tool_name pipeline"

# check python version ... should be 3.7 or newer
MIN_PYTHON = (3, 7)
try:
    assert sys.version_info >= MIN_PYTHON
except AssertionError:
    exit(
        f"{sys.argv[0]} requires Python {'.'.join([str(n) for n in MIN_PYTHON])} or newer"
    )

class Colors:
    """Class encoding for ANSI escape sequences for styling terminal text.
    Any string that is formatting with these styles must be terminated with
    the escape sequence, i.e. `Colors.end`.
    """

    # Escape sequence
    end = "\33[0m"
    # Formatting options
    bold = "\33[1m"
    italic = "\33[3m"
    url = "\33[4m"
    blink = "\33[5m"
    highlighted = "\33[7m"
    # Text Colors
    black = "\33[30m"
    red = "\33[31m"
    green = "\33[32m"
    yellow = "\33[33m"
    blue = "\33[34m"
    pink = "\33[35m"
    cyan = "\33[96m"
    white = "\33[37m"
    # Background fill colors
    bg_black = "\33[40m"
    bg_red = "\33[41m"
    bg_green = "\33[42m"
    bg_yellow = "\33[43m"
    bg_blue = "\33[44m"
    bg_pink = "\33[45m"
    bg_cyan = "\33[46m"
    bg_white = "\33[47m"


def err(*message, **kwargs):
    """Prints any provided args to standard error.
    kwargs can be provided to modify print functions
    behavior.
    @param message <any>:
        Values printed to standard error
    @params kwargs <print()>
        Key words to modify print function behavior
    """
    print(*message, file=sys.stderr, **kwargs)


def fatal(*message, **kwargs):
    """Prints any provided args to standard error
    and exits with an exit code of 1.
    @param message <any>:
        Values printed to standard error
    @params kwargs <print()>
        Key words to modify print function behavior
    """
    err(*message, **kwargs)
    sys.exit(1)


def _now():
    ct = datetime.now()
    now = ct.strftime("%y%m%d%H%M%S")
    return now


def _get_file_mtime(f):
    timestamp = datetime.fromtimestamp(os.path.getmtime(os.path.abspath(f)))
    mtime = timestamp.strftime("%y%m%d%H%M%S")
    return mtime


def exists(testpath):
    """Checks if file exists on the local filesystem.
    @param parser <argparse.ArgumentParser() object>:
        argparse parser object
    @param testpath <str>:
        Name of file/directory to check
    @return does_exist <boolean>:
        True when file/directory exists, False when file/directory does not exist
    """
    does_exist = True
    if not os.path.exists(testpath):
        does_exist = False  # File or directory does not exist on the filesystem

    return does_exist


def exe_in_path(cmd, path=None):
    """Checks if an executable is in $PATH
    @param cmd <str>:
        Name of executable to check
    @param path <list>:
        Optional list of PATHs to check [default: $PATH]
    @return <boolean>:
        True if exe in PATH, False if not in PATH
    """
    if path is None:
        path = os.environ["PATH"].split(os.pathsep)

    for prefix in path:
        filename = os.path.join(prefix, cmd)
        executable = os.access(filename, os.X_OK)
        is_not_directory = os.path.isfile(filename)
        if executable and is_not_directory:
            return True
    return False


def permissions(parser, filename, *args, **kwargs):
    """Checks permissions using os.access() to see the user is authorized to access
    a file/directory. Checks for existence, readability, writability and executability via:
    os.F_OK (tests existence), os.R_OK (tests read), os.W_OK (tests write), os.X_OK (tests exec).
    @param parser <argparse.ArgumentParser() object>:
        Argparse parser object
    @param filename <str>:
        Name of file to check
    @return filename <str>:
        If file exists and user can read from file
    """
    if not exists(filename):
        parser.error(
            "File '{}' does not exists! Failed to provide valid input.".format(filename)
        )

    if not os.access(filename, *args, **kwargs):
        parser.error(
            "File '{}' exists, but cannot read file due to permissions!".format(
                filename
            )
        )

    return filename

def _cp_r_safe_(source, target, resources=[]):
    """Private function: Given a list paths it will recursively copy each to the
    target location. If a target path already exists, it will NOT over-write the
    existing paths data.
    @param resources <list[str]>:
        List of paths to copy over to target location
    @params source <str>:
        Add a prefix PATH to each resource
    @param target <str>:
        Target path to copy templates and required resources
    """
    for resource in resources:
        destination = os.path.join(target, resource)
        if not exists(destination):
            # Required resources do not exist
            copytree(os.path.join(source, resource), destination)



def rename(filename):
    """Dynamically renames FastQ file to have one of the following extensions: *.R1.fastq.gz, *.R2.fastq.gz
    To automatically rename the fastq files, a few assumptions are made. If the extension of the
    FastQ file cannot be infered, an exception is raised telling the user to fix the filename
    of the fastq files.
    @param filename <str>:
        Original name of file to be renamed
    @return filename <str>:
        A renamed FastQ filename
    """
    # Covers common extensions from SF, SRA, EBI, TCGA, and external sequencing providers
    # key = regex to match string and value = how it will be renamed
    extensions = {
        # Matches: _R[12]_fastq.gz, _R[12].fastq.gz, _R[12]_fq.gz, etc.
        ".R1.f(ast)?q.gz$": ".R1.fastq.gz",
        ".R2.f(ast)?q.gz$": ".R2.fastq.gz",
        # Matches: _R[12]_001_fastq_gz, _R[12].001.fastq.gz, _R[12]_001.fq.gz, etc.
        # Capture lane information as named group
        ".R1.(?P<lane>...).f(ast)?q.gz$": ".R1.fastq.gz",
        ".R2.(?P<lane>...).f(ast)?q.gz$": ".R2.fastq.gz",
        # Matches: _[12].fastq.gz, _[12].fq.gz, _[12]_fastq_gz, etc.
        "_1.f(ast)?q.gz$": ".R1.fastq.gz",
        "_2.f(ast)?q.gz$": ".R2.fastq.gz"
    }

    if (filename.endswith('.R1.fastq.gz') or
        filename.endswith('.R2.fastq.gz') or 
        filename.endswith('.bam')):
        # Filename is already in the correct format
        return filename

    converted = False
    for regex, new_ext in extensions.items():
        matched = re.search(regex, filename)
        if matched:
            # regex matches with a pattern in extensions
            converted = True
            filename = re.sub(regex, new_ext, filename)
            break # only rename once

    if not converted:
        raise NameError("""\n\tFatal: Failed to rename provided input '{}'!
        Cannot determine the extension of the user provided input file.
        Please rename the file list above before trying again.
        Here is example of acceptable input file extensions:
          sampleName.R1.fastq.gz      sampleName.R2.fastq.gz
          sampleName_R1_001.fastq.gz  sampleName_R2_001.fastq.gz
          sampleName_1.fastq.gz       sampleName_2.fastq.gz
        Please also check that your input files are gzipped?
        If they are not, please gzip them before proceeding again.
        """.format(filename, sys.argv[0])
        )

    return filename


def _sym_safe_(input_data, target):
    """Creates re-named symlinks for each FastQ file provided
    as input. If a symlink already exists, it will not try to create a new symlink.
    If relative source PATH is provided, it will be converted to an absolute PATH.
    @param input_data <list[<str>]>:
        List of input files to symlink to target location
    @param target <str>:
        Target path to copy templates and required resources
    @return input_fastqs list[<str>]:
        List of renamed input FastQs
    """
    input_fastqs = []  # store renamed fastq file names
    for file in input_data:
        filename = os.path.basename(file)
        renamed = os.path.join(target, rename(filename))
        input_fastqs.append(renamed)

        if not exists(renamed):
            # Create a symlink if it does not already exist
            # Follow source symlinks to resolve any binding issues
            os.symlink(os.path.abspath(os.path.realpath(file)), renamed)

    return input_fastqs

def initialize(sub_args, repo_path, output_path):
    """Initialize the output directory and copy over required pipeline resources.
    If user provides a output directory path that already exists on the filesystem
    as a file (small chance of happening but possible), a OSError is raised. If the
    output directory PATH already EXISTS, it will not try to create the directory.
    If a resource also already exists in the output directory (i.e. output/workflow),
    it will not try to copy over that directory. In the future, it maybe worth adding
    an optional cli arg called --force, that can modify this behavior. Returns a list
    of renamed FastQ files (i.e. renamed symlinks).
    @param sub_args <parser.parse_args() object>:
        Parsed arguments for run sub-command
    @param repo_path <str>:
        Path to tool_name source code and its templates
    @param output_path <str>:
        Pipeline output path, created if it does not exist
    @return inputs list[<str>]:
        List of pipeline's input FastQ files
    """
    if not exists(output_path):
        # Pipeline output directory does not exist on filesystem
        os.makedirs(output_path)

    elif exists(output_path) and os.path.isfile(output_path):
        # Provided Path for pipeline output directory exists as file
        raise OSError(
            """\n\tFatal: Failed to create provided pipeline output directory!
        User provided --output PATH already exists on the filesystem as a file.
        Please run {} again with a different --output PATH.
        """.format(
                sys.argv[0]
            )
        )

    # Copy over templates are other required resources
    required_resources = ["workflow", "resources", "config"]
    _cp_r_safe_(source=repo_path, target=output_path, resources=required_resources)

    # Create renamed symlinks to rawdata
    inputs = _sym_safe_(input_data=sub_args.input, target=output_path)

    return inputs


def join_jsons(templates):
    """Joins multiple JSON files to into one data structure
    Used to join multiple template JSON files to create a global config dictionary.
    @params templates <list[str]>:
        List of template JSON files to join together
    @return aggregated <dict>:
        Dictionary containing the contents of all the input JSON files
    """
    # Get absolute PATH to templates in the tool_name git repo
    repo_path = os.path.dirname(os.path.abspath(__file__))
    aggregated = {}

    for file in templates:
        with open(os.path.join(repo_path, file), "r") as fh:
            aggregated.update(json.load(fh))

    return aggregated

def join_yamls(templates):
    """Joins multiple YAML files to into one data structure
    Used to join multiple template YAML files to create a global config dictionary.
    @params templates <list[str]>:
        List of template YAML files to join together
    @return aggregated <dict>:
        Dictionary containing the contents of all the input YAML files
    """
    # Get absolute PATH to templates in the tool_name git repo
    repo_path = os.path.dirname(os.path.abspath(__file__))
    aggregated = {}

    for file in templates:
        with open(os.path.join(repo_path, file), "r") as fh:
            aggregated.update(yaml.load(fh, Loader=yaml.FullLoader))

    return aggregated


def add_user_information(config):
    """Adds username and user's home directory to config.
    @params config <dict>:
        Config dictionary containing metadata to run pipeline
    @return config <dict>:
         Updated config dictionary containing user information (username and home directory)
    """
    # Get PATH to user's home directory
    # Method is portable across unix-like OS and Windows
    home = os.path.expanduser("~")

    # Get username from home directory PATH
    username = os.path.split(home)[-1]

    # Update config with home directory and username
    config["config"]["userhome"] = home
    config["config"]["username"] = username

    return config

def add_sample_metadata(input_files, config):
    """Adds sample metadata such as sample basename, label, and group information.
    If sample sheet is provided, it will default to using information in that file.
    If no sample sheet is provided, it will only add sample basenames and labels.
    @params input_files list[<str>]:
        List containing pipeline input fastq files
    @params config <dict>:
        Config dictionary containing metadata to run pipeline
    @params group <str>:
        Sample sheet containing basename, group, and label for each sample
    @return config <dict>:
        Updated config with basenames, labels, and groups (if provided)
    """
    added = []
    for file in input_files:
        # Split sample name on file extension
        sample = re.split("\.R[12]\.fastq\.gz", os.path.basename(file))[0]
        if sample not in added:
            # Only add PE sample information once
            added.append(sample)
            config["config"]["groups"]["rsamps"].append(sample)
            config["config"]["groups"]["rgroups"].append(sample)
            config["config"]["groups"]["rlabels"].append(sample)
            config["config"]["erv_samplemanifest"].append(sample)

    return config

def add_rawdata_information(sub_args, config, ifiles):
    """Adds information about rawdata provided to pipeline.
    Determines whether the dataset is paired-end or single-end and finds the set of all
    rawdata directories (needed for -B option when running singularity). If a user provides
    paired-end data, checks to see if both mates (R1 and R2) are present for each sample.
    @param sub_args <parser.parse_args() object>:
        Parsed arguments for run sub-command
    @params ifiles list[<str>]:
        List containing pipeline input files (renamed symlinks)
    @params config <dict>:
        Config dictionary containing metadata to run pipeline
    @return config <dict>:
         Updated config dictionary containing user information (username and home directory)
    """
    # Add each sample's basename, label and group info
    config = add_sample_metadata(input_files=ifiles, config=config)

    return config

def setup(sub_args, ifiles, output_path):
    """Setup the pipeline for execution and creates config file from templates
    @param sub_args <parser.parse_args() object>:
        Parsed arguments for run sub-command
    @param repo_path <str>:
        Path to tool_name source code and its templates
    @param output_path <str>:
        Pipeline output path, created if it does not exist
    @return config <dict>:
         Config dictionary containing metadata to run the pipeline
    @return hpcname <str>:
    """
    # Resolves PATH to template for genomic reference files to select from a
    # bundled reference genome via the tool_name build subcommand
    hpcname ="biowulf"
    version = __version__
    print("Thank you for running tool_name",version,"pipeline on BIOWULF!")

    if str(sub_args.viral).lower() == 'true':
        genome_config = os.path.join(
            output_path, "config", "genomes", sub_args.genome + "+viral" +".yaml")
        #print("--viral flag added. Will use custom host+viral reference genomes for tool_name pipeline")
    else:
        genome_config = os.path.join(
            output_path, "config", "genomes", sub_args.genome + ".yaml")
    
    required = {
        "base": os.path.join(output_path,'config','config.yaml'),
        "genome": genome_config,
        "tools": os.path.join(output_path, "config", "tools.yaml"),
        "cluster_tools": os.path.join(output_path, "config", "cluster_tools.yaml")
    }
    cluster_config = os.path.join(output_path,'resources', 'cluster.yaml')
    cluster_output = os.path.join(output_path, 'cluster.yaml')
    copyfile(cluster_config,cluster_output)

    # Global config file for pipeline, config.json
    config = join_yamls(required.values())  # uses templates in the tool_name repo
    config = add_user_information(config)
    config = add_rawdata_information(sub_args, config, ifiles)

    # Add other cli collected info
    config["config"]["annotation"] = sub_args.genome
    config["config"]["version"] = __version__
    config["config"]["pipehome"] = os.path.dirname(__file__)
    config["config"]["workpath"] = os.path.abspath(sub_args.output)
    config["config"]["genome"] = sub_args.genome

    # Add ERVpipeline related info
    config["config"]["erv_scriptsdir"] = os.path.join(output_path,'workflow', 'scripts')
    config["config"]["erv_resourcesdir"] = os.path.join(output_path, 'resources')


    # Add optional cli workflow steps
    config["options"] = {}
    config["options"]["tmp_dir"] = sub_args.tmp_dir

    

    # Save config to output directory
    print(
        "\nGenerating config file in '{}'... ".format(
            os.path.join(output_path, "config.yaml")
        ),
        end="",
    )
    # print(yaml.dumps(config, indent = 4, sort_keys=True))
    with open(os.path.join(output_path, "config.yaml"), "w") as fh:
        yaml.dump(config, fh, indent=4, sort_keys=True)
    print("Done!")

    return config, hpcname

def which(cmd, path=None):
    """Checks if an executable is in $PATH
    @param cmd <str>:
        Name of executable to check
    @param path <list>:
        Optional list of PATHs to check [default: $PATH]
    @return <boolean>:
        True if exe in PATH, False if not in PATH
    """
    if path is None:
        path = os.environ["PATH"].split(os.pathsep)

    for prefix in path:
        filename = os.path.join(prefix, cmd)
        executable = os.access(filename, os.X_OK)
        is_not_directory = os.path.isfile(filename)
        if executable and is_not_directory:
            return True
    return False

def require(cmds, suggestions, path=None):
    """Enforces an executable is in $PATH
    @param cmds list[<str>]:
        List of executable names to check
    @param suggestions list[<str>]:
        Name of module to suggest loading for a given index
        in param cmd.
    @param path list[<str>]]:
        Optional list of PATHs to check [default: $PATH]
    """
    error = False
    for i in range(len(cmds)):
        available = which(cmds[i])
        if not available:
            error = True
            err(
                """\x1b[6;37;41m\n\tFatal: {} is not in $PATH and is required during runtime!
            └── Solution: please 'module load {}' and run again!\x1b[0m""".format(
                    cmds[i], suggestions[i]
                )
            )

    if error:
        fatal()

    return

def dryrun(
    outdir,
    config="config.yaml",
    snakefile=os.path.join("workflow", "Snakefile"),
    write_to_file=True,
):
    """Dryruns the pipeline to ensure there are no errors prior to running.
    @param outdir <str>:
        Pipeline output PATH
    @return dryrun_output <str>:
        Byte string representation of dryrun command
    """
    try:
        dryrun_output = subprocess.check_output(
            [
                "snakemake",
                "-npr",
                "-s",
                str(snakefile),
                "--cores",
                "4",
                "--configfile={}".format(config),
            ],
            cwd=outdir,
            stderr=subprocess.STDOUT,
        )

    except subprocess.CalledProcessError as e:
        # Tell user to load main dependencies to avoid the OSError below
        print(
            "Something went wrong in the snakemake run! Please check config.yaml file!"
        )
        sys.exit("{}\n{}".format(e, e.output.decode("utf-8")))
    except OSError as e:
        # Catch: OSError: [Errno 2] No such file or directory
        #  Occurs when command returns a non-zero exit-code
        if e.errno == 2 and not exe_in_path("snakemake"):
            # Failure caused because snakemake is NOT in $PATH
            print(
                "\x1b[6;37;41m\nError: Is snakemake in your $PATH?\nPlease check before proceeding again!\x1b[0m",
                file=sys.stderr,
            )
            sys.exit("{}".format(e))
        else:
            # Failure caused by unknown cause, raise error
            raise e

    if write_to_file:
        now = _now()
        with open(os.path.join(outdir, "dryrun." + str(now) + ".log"), "w") as outfile:
            outfile.write("{}".format(dryrun_output.decode("utf-8")))

    return dryrun_output


def orchestrate(
    mode,
    outdir,
    threads=2,
    submission_script="runner",
    masterjob="pl:tool_name",
    tmp_dir="/lscratch/$SLURM_JOBID/",
    hpcname="",
):
    """Runs the tool_name pipeline via selected executor: local or slurm.
    If 'local' is selected, the pipeline is executed locally on a compute node/instance.
    If 'slurm' is selected, jobs will be submitted to the cluster using SLURM job scheduler.
    @param outdir <str>:
        Pipeline output PATH
    @param mode <str>:
        Execution method or mode:
            local runs serially a compute instance without submitting to the cluster.
            slurm will submit jobs to the cluster using the SLURM job scheduler.
    @param threads <str>:
        Number of threads to use for local execution method
    @param submission_script <str>:
        Path to master jobs submission script:
            tool_name run =   /path/to/output/resources/runner
    @param masterjob <str>:
        Name of the master job
    @param tmp_dir <str>:
        Absolute Path to temp dir for compute node
    @param hpcname <str>:
        "biowulf" if run on biowulf, "frce" if run on frce, blank otherwise. hpcname is determined in setup() function
    @return masterjob <subprocess.Popen() object>:
    """
 
    outdir = os.path.abspath(outdir)

    if not exists(os.path.join(outdir, "logfiles")):
        # Create directory for logfiles
        os.makedirs(os.path.join(outdir, "logfiles"))

    if exists(os.path.join(outdir, "logfiles", "snakemake.log")):
        mtime = _get_file_mtime(os.path.join(outdir, "logfiles", "snakemake.log"))
        newname = os.path.join(outdir, "logfiles", "snakemake." + str(mtime) + ".log")
        os.rename(os.path.join(outdir, "logfiles", "snakemake.log"), newname)

    # Run on compute node or instance without submitting jobs to a scheduler
    if mode == "local":
        # Run tool_name: instantiate main/master process
        # Look into later: it maybe worth replacing Popen subprocess with a direct
        # snakemake API call: https://snakemake.readthedocs.io/en/stable/api_reference/snakemake.html
        # Create log file for pipeline
        logfh = open(os.path.join(outdir, "logfiles", "snakemake.log"), "w")
        masterjob = subprocess.Popen(
            [
                "snakemake",
                "-pr",
                "--cores",
                str(threads),
                "--configfile=config.yaml",
            ],
            cwd=outdir
        )

    # Submitting jobs to cluster via SLURM's job scheduler
    elif mode == "slurm":
        # Run tool_name: instantiate main/master process
        # Look into later: it maybe worth replacing Popen subprocess with a direct
        # snakemake API call: https://snakemake.readthedocs.io/en/stable/api_reference/snakemake.html
        # snakemake --latency-wait 120  -s $R/Snakefile -d $R --printshellcmds
        #    --cluster-config $R/cluster.json --keep-going --restart-times 3
        #    --cluster "sbatch --gres {cluster.gres} --cpus-per-task {cluster.threads} -p {cluster.partition} -t {cluster.time} --mem {cluster.mem} --job-name={params.rname}"
        #    -j 500 --rerun-incomplete --stats $R/Reports/initialqc.stats -T
        #    2>&1| tee -a $R/Reports/snakemake.log

        # Create log file for master job information
        logfh = open(os.path.join(outdir, "logfiles", "master.log"), "w")
        # submission_script for tool_name run is /path/to/output/resources/runner
        # submission_script for tool_name build is /path/to/output/resources/builder
        cmdlist = [
            str(os.path.join(outdir, "resources", str(submission_script))),
            mode,
            "-j",
            str(masterjob),
            "-o",
            str(outdir),
            "-t",
            str(tmp_dir),
        ]
        if str(hpcname) != "":
            cmdlist.append("-n")
            cmdlist.append(hpcname)
        else:
            cmdlist.append("-n")
            cmdlist.append("unknown")

        print(" ".join(cmdlist))
        masterjob = subprocess.Popen(
            cmdlist, cwd=outdir, stderr=subprocess.STDOUT, stdout=logfh
        )

    return masterjob


def run(sub_args):
    """Initialize, setup, and run the tool_name pipeline.
    Calls initialize() to create output directory and copy over pipeline resources,
    setup() to create the pipeline config file, dryrun() to ensure their are no issues
    before running the pipeline, and finally run() to execute the Snakemake workflow.
    @param sub_args <parser.parse_args() object>:
        Parsed arguments for run sub-command
    """
    require(["snakemake", "ccbrpipeliner"], ["snakemake", "ccbrpipeliner"])

    # Get PATH to the tool_name git repository for copying over pipeline resources
    
    # Initialize working directory, copy over required pipeline resources
    input_files = initialize(sub_args, repo_path=tool_name_path, output_path=sub_args.output)


    # Step pipeline for execution, create config.json config file from templates
    # hpcname is either biowulf or frce or blank
    config, hpcname = setup(
        sub_args, ifiles=input_files, output_path=sub_args.output)

    # Optional Step: Dry-run pipeline
    if sub_args.dry_run:
        dryrun_output = dryrun(
            outdir=sub_args.output
        )  # python3 returns byte-string representation
        print("\nDry-running tool_name pipeline:\n{}".format(dryrun_output.decode("utf-8")))
        sys.exit(0) 

    # Run pipeline
    masterjob = orchestrate(
        mode=sub_args.mode,
        outdir=sub_args.output,
        threads=sub_args.threads,
        tmp_dir=sub_args.tmp_dir,
        hpcname=hpcname,
    )

    # Wait for subprocess to complete,
    # this is blocking
    masterjob.wait()

    # Relay information about submission
    # of the master job or the exit code of the
    # pipeline that ran in local mode
    if sub_args.mode == "local":
        if int(masterjob.returncode) == 0:
            print("{} pipeline has successfully completed".format(_name))
        else:
            fatal(
                "{} pipeline failed. Please see standard output for more information."
            )
    elif sub_args.mode == "slurm":
        jobid = (
            open(os.path.join(sub_args.output, "logfiles", "mjobid.log")).read().strip()
        )
        if int(masterjob.returncode) == 0:
            print("Successfully submitted master job: ", end="")
        else:
            fatal(
                "Error occurred when submitting the master job. Error code = {}".format(
                    masterjob.returncode
                )
            )
        print(jobid)


def genome_options(parser, user_option, prebuilt):
    """Dynamically checks if --genome option is a valid choice. Compares against a
    list of prebuilt or bundled genome reference genomes and accepts a custom reference
    genome that was built using the 'tool_name build' command. The ability to also
    accept a custom reference YAML file allows for chaining of the tool_name build and run
    commands in succession.
    @param parser <argparse.ArgumentParser object>:
        Parser object from which an exception is raised not user_option is not valid
    @param user_option <str>:
        Provided value to the tool_name run, --genome argument
    @param prebuilt list[<str>]:
        List of prebuilt reference genomes
    return user_option <str>:
        Provided value to the tool_name run, --genome argument
        If value is not valid or custom reference genome JSON file not readable,
        an exception is raised.
    """
    # Checks for custom built genomes using tool_name build
    if user_option.endswith(".yaml"):
        # Check file is readable or accessible
        permissions(parser, user_option, os.R_OK)
    # Checks against valid pre-built options
    elif not user_option in prebuilt:
        # User did NOT provide a valid choice
        parser.error(
            """provided invalid choice, '{}', to --genome argument!\n
        Choose from one of the following pre-built genome options: \n
        \t{}\n
        """
        )

    return user_option

console = Console()
ascii_banner = f"""
[cyan]
██╗     ██╗██████╗ ███████╗██████╗ ████████╗██╗   ██╗
██║     ██║██╔══██╗██╔════╝██╔══██╗╚══██╔══╝╚██╗ ██╔╝
██║     ██║██████╔╝█████╗  ██████╔╝   ██║    ╚████╔╝ 
██║     ██║██╔══██╗██╔══╝  ██╔══██╗   ██║     ╚██╔╝  
███████╗██║██████╔╝███████╗██║  ██║   ██║      ██║   
╚══════╝╚═╝╚═════╝ ╚══════╝╚═╝  ╚═╝   ╚═╝      ╚═╝   
                                                     
[/cyan]
[magenta] [bold] Version:  {__version__} [/bold] [/magenta] 
"""
styled_name = "[bold]tool_name: TODO oneline description of TOOL_NAME[/bold]"

def parsed_arguments(name, description):
    """Parses user-provided command-line arguments. Requires argparse and textwrap
    package. argparse was added to standard lib in python 3.2 and textwrap was added
    in python 3.5. To create custom help formatting for subparsers a docstring is
    used create the help message for required options. argparse does not support named
    subparser groups, which is normally what would be used to accomphish this reformatting.
    As so, the help message for require options must be suppressed. If a new required arg
    is added to a subparser, it must be added to the docstring and the usage statement
    also must be updated.
    @param name <str>:
        Name of the pipeline or command-line tool
    @param description <str>:
        Short description of pipeline or command-line tool
    """

    console.print(ascii_banner)
    console.print(styled_name, "\n")
    c = Colors
    pipe_name = ""
    description = ""

    # Create a top-level parser
    parser = argparse.ArgumentParser()

    # Adding Version information
    parser.add_argument(
        "--version", action="version", version="%(prog)s {}".format(__version__)
    )

    # Create sub-command parser
    subparsers = parser.add_subparsers(help="List of available sub-commands")

    # Options for the "run" sub-command
    # Grouped sub-parser arguments are currently not supported by argparse.
    # https://bugs.python.org/issue9341
    # Here is a work around to create more useful help message for named
    # options that are required! Please note: if a required arg is added the
    # description below should be updated (i.e. update usage and add new option)
    required_run_options = textwrap.dedent(
        """
        {1}{0} {3}run{4}: {1} Runs the tool_name pipeline.{4}

        {1}{2}Synopsis:{4}
          $ {0} run [--help] \\
                              [--dry-run] [--mode {{slurm, local}}] \\
                              --input INPUT [INPUT ...] \\
                              --genome {{mm10, hg38}} \\
                              [--viral] \\
                              --output OUTPUT

        {1}{2}Description:{4}
          To run the pipeline with with your data, please provide a space separated
        list of FastQs (globbing is supported), an output directory to store results,
        and a reference genome.

        {1}{2}Required arguments:{4}
          --input INPUT [INPUT ...]
                                Input FastQ file(s) to process. One or more FastQ files
                                can be provided. The pipeline supports only pair-end RNA-seq data.
                                  Example: --input .tests/*.R?*.fastq.gz

          --genome 
                                Reference genome. 
                                Example: --genome hg38
                                {{mm10, hg38}}
                                
          --output OUTPUT
                                Path to an output directory. This location is where
                                the pipeline will create all of its output files, also
                                known as the pipeline's working directory. If the user
                                provided working directory has not been initialized,
                                it will be created automatically.
                                  Example: --output /data/$USER/RNA_hg38
                                

        {1}{2}Orchestration options:{4}
          --dry-run             Does not execute anything. Only displays what steps in
                                the pipeline remain or will be run.
                                  Example: --dry-run

          --mode {{slurm,local}}
                                Method of execution. Defines the mode of execution.
                                Valid options for this mode include: local or slurm.
                                Additional modes of execution are coming soon, default:
                                slurm.
                                Here is a brief description of each mode:
                                   • local: uses local method of execution. local runs
                                will run serially on compute instance. This is useful
                                for testing, debugging, or when a users does not have
                                access to a  high  performance  computing environment.
                                If this option is not provided, it will default to a
                                slurm mode of execution.
                                   • slurm: uses slurm execution backend. This method
                                will submit jobs to a  cluster  using sbatch. It is
                                recommended running the pipeline in this mode as it
                                will be significantly faster.
                                  Example: --mode slurm

        {1}{2}Misc Options:{4}
          --viral               To include viral sequences from RefSeq database using custom host+viral genomes.
                                  Example: --viral
          -h, --help            Show usage information, help message, and exit.
                                  Example: --help                        
        """.format(
            name, c.bold, c.url, c.italic, c.end
        )
    )
        # Display example usage in epilog
    run_epilog = textwrap.dedent(
        """\
        Example:
            # login to Biowulf
            ssh -Y -o ServerAliveInterval=60 username@biowulf.nih.gov

            # grab an interactive node on biowulf
            sinteractive --mem=50g --cpus-per-task=8

            # Load snakemake
            module load snakemake

            # Define variables with input and output directories
            INDIR="/absolute/path/to/your/input/fastq/folder"
            OUTDIR="/absolute/path/to/your/output/folder"

            # Run the pipeline 

            #### Step1: Dry-run the pipeline

            ./tool_name run \\
            --dry-run \\
            --input $INDIR/*R?*.fastq.gz  \\
            --genome hg38 \\ # available genomes = mm10, hg38
            --mode slurm \\
            --output $OUTDIR/hg38_run1 # All output will be stored in hg38_run1

            # With the --dry-run option, the pipeline will create the output folder
            # and copy all the necessary pipeline resources into it.

            #### Step2: Submit the pipeline

            ./tool_name run \\
            --input $INDIR/*R?*.fastq.gz  \\
            --genome hg38 \\ 
            --mode slurm \\
            --output $OUTDIR/hg38_run1 

        version:
          {}
        """.format(
            __version__
        )
    )

    # Suppressing help message of required args to overcome no sub-parser named groups
    subparser_run = subparsers.add_parser(
        "run",
        help="Run the tool_name pipeline.",
        usage=argparse.SUPPRESS,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=required_run_options,
        epilog=run_epilog,
        add_help=False,
    )

    # Required Arguments
    # Input FastQ files
    subparser_run.add_argument(
        "--input",
        # Check if the file exists and if it is readable
        type=lambda file: permissions(parser, file, os.R_OK),
        required=True,
        nargs="+",
        help=argparse.SUPPRESS,
    )

    # Output Directory,
    # analysis working directory
    subparser_run.add_argument(
        "--output",
        type=lambda option: os.path.abspath(os.path.expanduser(option)),
        required=True,
        help=argparse.SUPPRESS,
    )

    # Reference Genome, used for dynamically
    # selecting reference files
    subparser_run.add_argument(
        "--genome",
        required=True,
        type=lambda option: str(
            genome_options(subparser_run, option, ["mm10", "hg38"])
        ),
        help=argparse.SUPPRESS,
    )
        # Add host+viral custom genomes
    
    subparser_run.add_argument(
        "--viral",
        action="store_true",
        required=False,
        default=False,
        help=argparse.SUPPRESS
    )

    # Optional Arguments
    # Add custom help message
    subparser_run.add_argument("-h", "--help", action="help", help=argparse.SUPPRESS)

    # Orchestration options
    # Dry-run, do not execute the workflow,
    # prints what steps remain
    subparser_run.add_argument(
        "--dry-run",
        action="store_true",
        required=False,
        default=False,
        help=argparse.SUPPRESS,
    )

    # Execution Method, run locally
    # on a compute node or submit to
    # a supported job scheduler, etc.
    subparser_run.add_argument(
        "--mode",
        type=str,
        required=False,
        default="slurm",
        choices=["slurm", "local"],
        help=argparse.SUPPRESS,
    )

    # Base directory to write
    # temporary/intermediate files
    subparser_run.add_argument(
        "--tmp-dir",
        type=str,
        required=False,
        default="/lscratch/$SLURM_JOBID/",
        help=argparse.SUPPRESS,
    )

    # Number of threads for the
    # pipeline's main proceess
    # This is only applicable for
    # local rules or when running
    # in local mode.
    subparser_run.add_argument(
        "--threads", type=int, required=False, default=2, help=argparse.SUPPRESS
    )

    # Sub-parser for the "plot" sub-command
    # Grouped sub-parser arguments are currently not supported.
    # https://bugs.python.org/issue9341
    # Here is a work around to create more useful help message for named
    # options that are required! Please note: if a required arg is added the
    # description below should be updated (i.e. update usage and add new option)
    required_plot_options = textwrap.dedent(
        """
        {1}{0} {3}plot{4}: {1} Renders the tool_name pipeline summary report.{4}

        {1}{2}Synopsis:{4}
          $ {0} plot [--help] \\
                                --sampleFile \\
                                --results 

        {1}{2}Required arguments:{4}
          --sampleFile 
                                Path to the file containing sample information (see documentation).
                                The order of samples should be same as the rsamps: in config.yaml file.
                                Example: --sampleFile /data/$USER/sampleFile.txt
        
          --results 
                                Path to the folder containing results from the tool_name analysis.
                                Example: --results /data/$USER/tool_name_output/
        """.format(
            name, c.bold, c.url, c.italic, c.end)
    )

    # Display example usage in epilog
    plot_epilog = textwrap.dedent(
        """\
        Example:
          # Renders the tool_name pipeline summary report
          
          tool_name plot   \\
            --sampleFile /data/$USER/sampleFile.txt \\
            --results /data/$USER/tool_name_output 

        version:
          {}
        """.format(
            __version__
        )
    )

    # Suppressing help message of required args to overcome no sub-parser named groups
    subparser_plot = subparsers.add_parser(
        "plot",
        help="Renders the tool_name pipeline summary report.",
        usage=argparse.SUPPRESS,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=required_plot_options,
        epilog=plot_epilog,
        add_help=True
    )

    # Required Arguments
    
    # Sample Info file
    subparser_plot.add_argument(
        "--sampleFile",
        # Check if the file exists and if it is readable
        type=lambda file: permissions(parser, file, os.R_OK),
        required=True,
        help=argparse.SUPPRESS,
    )

    # Results Directory (combinedTables from the tool_name analysis)
    subparser_plot.add_argument(
        "--results",
        type=lambda option: os.path.abspath(os.path.expanduser(option)),
        required=True,
        help=argparse.SUPPRESS,
    )
    
    # Define handlers for each sub-parser
    subparser_run.set_defaults(func=run)
    subparser_plot.set_defaults(func=plot)

    # Parse command-line args
    args = parser.parse_args()
    return args

def main():

    # Sanity check for usage
    if len(sys.argv) == 1:
        # Nothing was provided
        fatal(ascii_banner,"\n","Invalid usage: {} [-h] [--version] ...".format(_name))

    # Collect args for sub-command
    args = parsed_arguments(name=_name, description=_description)

    # Display version information
    print("tool_name ({})".format(__version__))

    # Mediator method to call sub-command's set handler function
    args.func(args)
    


if __name__ == "__main__":
    main()
