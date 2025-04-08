# Snakemake Template <!-- TODO: replace this header with TOOL_NAME -->

CCBR template for creating Snakemake pipelines <!-- TODO: replace this line with the description of TOOL_NAME -->

[![build](https://github.com/CCBR/CCBR_SnakemakeTemplate/actions/workflows/build.yml/badge.svg)](https://github.com/CCBR/CCBR_SnakemakeTemplate/actions/workflows/build.yml) <!-- TODO: replace CCBR/CCBR_SnakemakeTemplate with your OWNER/TOOL_NAME -->

See the website for detailed information, documentation, and examples:
<https://ccbr.github.io/TOOL_NAME/>

## Using this template

1. Create a new repository from this template using either of these options:
   - [**The GitHub web interface**](https://github.com/CCBR/CCBR_SnakemakeTemplate):
     Click "Use this template" and "Create a new repository", then choose an owner (e.g. CCBR or another organization) and the repository name as the new tool's name.
   - [**The GitHub command line interface**](https://cli.github.com/):
     Replace `OWNER/TOOL_NAME` with your organization (e.g. CCBR) and the actual tool name.
     ```sh
     gh repo create OWNER/TOOL_NAME \
        --description "One-line description of your tool" \
        --public \
        --template CCBR/CCBR_SnakemakeTemplate \
        --confirm
     ```
1. Read and follow the contributing guidelines in `.github/CONTRIBUTING.md`.
   Be sure to [install `pre-commit` and its hooks](.github/CONTRIBUTING.md#use-pre-commit-hooks) before making any commits.
1. Change all instances of `TOOL_NAME` and `tool_name` throughout the repo with the actual tool name.
   Replace `TOOL_NAME` with the all-caps version (refers to the GitHub repo name)
   and `tool_name` with the lowercase version (refers to the command-line interface). Places include:

   <!--
   grep -irl tool_name . | sort | sed "s|\./||"
   -->

   ```
   .github/CONTRIBUTING.md
   .github/ISSUE_TEMPLATE/bug_report.yml
   .github/ISSUE_TEMPLATE/config.yml
   .github/workflows/build.yml
   bin/tool_name
   CHANGELOG.md
   CITATION.cff
   README.md
   main.nf
   mkdocs.yml
   pyproject.toml
   src/__main__.py
   ```

1. Edit `pyproject.toml` with correct metadata for your tool. You will likely need to change:
   - author names and emails
   - dependencies
   - project URLs
1. Write your Snakemake workflow.
1. Write your documentation in `docs/` and enable GitHub Pages.
   - In settings, go to General > Pages and select the `gh-pages` branch.
     mkdocs will build your site under the `gh-pages` branch, and GitHub Pages will make it available at `https://OWNER.github.io/TOOL_NAME`.
1. Edit the README:
   1. Change the title and description.
   1. Delete the section [Using this template](README.md##using-this-template).
1. You can look for instances of `TOOL_NAME` in case you missed any with grep:

   ```sh
   grep -ir "TOOL_NAME" .
   ```

   If your repo is not part of CCBR, you will also want to look for instances of "CCBR" and "CCR Collaborative Bioinformatics Resource" and replace them with your organization.

   ```sh
   grep -ir "CCBR\|CCR" .
   ```

For a work-in-progress example of this template in action, see the [CHAMPAGNE](https://github.com/CCBR/CHAMPAGNE) repo.

## Usage

Install the tool in edit mode:

```sh
pip3 install -e .
```

Run the example

```sh
TOOL_NAME run --input "Hello world"
```

![dag](assets/dag.png)

## Help & Contributing

Come across a **bug**? Open an [issue](https://github.com/CCBR/TOOL_NAME/issues) and include a minimal reproducible example.

Have a **question**? Ask it in [discussions](https://github.com/CCBR/TOOL_NAME/discussions).

Want to **contribute** to this project? Check out the [contributing guidelines](docs/contributing.md).

## References

This repo was originally generated from the [CCBR Snakemake Template](https://github.com/CCBR/CCBR_SnakemakeTemplate).
The template takes inspiration from nektool[^1] and snaketool[^2]

[^1]: nektool https://github.com/beardymcjohnface/nektool
[^2]: snaketool https://github.com/beardymcjohnface/Snaketool
