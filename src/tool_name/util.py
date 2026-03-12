import pathlib

def tool_name_base(*paths, debug=False):
    """Get the absolute path to a file in the repository
    @return abs_path <str>
    """
    src_file = pathlib.Path(__file__).absolute()
    if debug:
        print("SRC FILE:", src_file)
    basedir = src_file.parent.parent.parent
    return str(basedir.joinpath(*paths))

def get_version(debug=False):
    """Get the current tool_name version
    @return version <str>
    """
    version_file = tool_name_base("VERSION")
    if debug:
        print("VERSION FILE:", version_file)
    with open(version_file, "r") as vfile:
        version = f"v{vfile.read().strip()}"
    return version
