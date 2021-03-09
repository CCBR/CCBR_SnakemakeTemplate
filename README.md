# CCBR Snakemake Pipeline Cookiecutter
This is a dummy folder framework for CCBR snakemake workflows.
New workflows can be started using this repository as a template.


## Creating new repository
You can use [gh cli](https://cli.github.com/) to
 * create a new repository under CCBR
 * copy over the template code from CCBR_SnakemakePipelineCookiecutter
with the following command
```
gh repo create CCBR/<reponame> 
--description "<repo description>" \
--public \
--template CCBR/CCBR_SnakemakePipelineCookiecutter \
--confirm
```
On biowulf, you may have to specify the full path of the `gh` executable:
```
/data/CCBR_Pipeliner/db/PipeDB/bin/gh_1.7.0_linux_amd64/bin/gh repo create CCBR/<reponame> 
--description "<repo description>" \
--public \
--template CCBR/CCBR_SnakemakePipelineCookiecutter \
--confirm
```
Then you can clone a local copy of the new repository:
```
git clone https://github.com/CCBR/<reponame>.git
```
