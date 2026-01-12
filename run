#!/usr/bin/env bash
set -eo pipefail
module purge

# Author: NameHere, PhD
# CCBR, NCI
# (c) 2023
#
# wrapper script to run the snakemake pipeline
# a) on an interactive node (runlocal) OR
# b) submit to the slurm load scheduler (run)
#

# setting python and snakemake versions
PYTHON_VERSION="python/3.9"
SNAKEMAKE_VERSION="snakemake/7.19.1"

#define cluster, partitions dependent on host
hostID=`echo $HOSTNAME`
if [[ $hostID == "biowulf.nih.gov" ]]; then
  BUYINPARTITIONS=$(bash <(curl -s https://raw.githubusercontent.com/CCBR/Tools/master/Biowulf/get_buyin_partition_list.bash 2>/dev/null))
  PARTITIONS="norm,ccr"
  cluster_specific_yaml="cluster_biowulf.yaml"
  tools_specific_yaml="tools_biowulf.yaml"
  #if [ $BUYINPARTITIONS ];then PARTITIONS="norm,$BUYINPARTITIONS";fi
elif [[ $hostID == "biowulf8.nih.gov" ]]; then
  PARTITIONS="rhel8"
  cluster_specific_yaml="cluster_rhel8.yaml"
  tools_specific_yaml="tools_rhel8.yaml"
fi

# set extra singularity bindings
EXTRA_SINGULARITY_BINDS="/lscratch, /data/CCBR_Pipeliner/"
SCRIPTNAME="$0"
SCRIPTDIRNAME=$(readlink -f $(dirname $0))
SCRIPTBASENAME=$(readlink -f $(basename $0))


# essential files
# these are relative to the workflows' base folder
# these are copied into the WORKDIR
ESSENTIAL_FILES="config/config.yaml config/samples.tsv config/fqscreen_config.conf config/multiqc_config.yaml resources/cluster_* resources/tools_*"
ESSENTIAL_FOLDERS="workflow/scripts"


function get_git_commitid_tag() {
  # This function gets the latest git commit id and tag
  # @Input:
  #   @param1: PIPELINE_HOME folder which is a initialized git repo folder path
  # @Output:
  #   @param1: tab-delimited commit id and tag

    cd $1
    gid=$(git rev-parse HEAD)
    tag=$(git describe --tags $gid 2>/dev/null)
    echo -ne "$gid\t$tag"
}

## setting PIPELINE_HOME
PIPELINE_HOME=$(readlink -f $(dirname "$0"))
echo "Pipeline Dir: $PIPELINE_HOME"
# set snakefile
SNAKEFILE="${PIPELINE_HOME}/workflow/Snakefile"
echo "Snakefile: $SNAKEFILE"
# get github commit tag
GIT_COMMIT_TAG=$(get_git_commitid_tag $PIPELINE_HOME)
echo "Git Commit/Tag: $GIT_COMMIT_TAG"

function usage() { 
# This function prints generic usage of the wrapper script.
  echo "${SCRIPTBASENAME}
  --> run CARLISLE
  Cut And Run anaLysIS pipeLinE

  USAGE:
    bash ${SCRIPTNAME} -m/--runmode=<RUNMODE> -w/--workdir=<WORKDIR>
  Required Arguments:
  1.  RUNMODE: [Type: String] Valid options:
      *) init : initialize workdir
      *) run : run with slurm
      *) reset : DELETE workdir dir and re-init it
      *) dryrun : dry run snakemake to generate DAG
      *) unlock : unlock workdir if locked by snakemake
      *) runlocal : run without submitting to sbatch
      *) testrun: run on cluster with included test dataset
  2.  WORKDIR: [Type: String]: Absolute or relative path to the output folder with write permissions.
  "
}

function err() { 
# This is a generic error message function. It prints the message, then the 
# usage and exits with non-zero exit code.
# @Input:
#     @param1: Message to print before printing the usage and exiting
# @Ouput:
#     @param2: echo the error message with the usage to the screen

cat <<< "
#################################################################
##### ERROR ############ ERROR ########## ERROR #################
#################################################################
  $@
" && usage_only && exit 1 1>&2; 
}

function init() {
  # This function initializes the workdir by:
  # 1. creating the working dir
  # 2. copying essential files like config.yaml and samples.tsv into the workdir
  # 3. setting up logs and stats folders

    # create output folder
    if [ -d $WORKDIR ];then err "Folder $WORKDIR already exists!"; fi
    mkdir -p $WORKDIR

    # copy essential files
    if [[ ! -d $WORKDIR/config ]]; then mkdir $WORKDIR/config; fi
    for f in $ESSENTIAL_FILES; do
      echo "Copying essential file: $f"
      fbn=$(basename $f)
      sed -e "s/PIPELINE_HOME/${PIPELINE_HOME//\//\\/}/g" -e "s/WORKDIR/${WORKDIR//\//\\/}/g" ${PIPELINE_HOME}/$f > $WORKDIR/config/$fbn
    done
    # rename config dependent on partition used
    cp $WORKDIR/config/$cluster_specific_yaml $WORKDIR/config/cluster.yaml
    cp $WORKDIR/config/$tools_specific_yaml $WORKDIR/config/tools.yaml

    # copy essential folders
    for f in $ESSENTIAL_FOLDERS;do
      rsync -avz --no-perms --no-owner --no-group --progress $PIPELINE_HOME/$f $WORKDIR/
    done

    #create log and stats folders
    if [ ! -d $WORKDIR/logs ]; then mkdir -p $WORKDIR/logs;echo "Logs Dir: $WORKDIR/logs";fi
    if [ ! -d $WORKDIR/stats ];then mkdir -p $WORKDIR/stats;echo "Stats Dir: $WORKDIR/stats";fi

    echo"#################################################################"
    echo"#################################################################"
    echo"Done Initializing $WORKDIR."
    echo"You can now edit $WORKDIR/config.yaml and $WORKDIR/samples.tsv"
    echo"#################################################################"
    echo"#################################################################"
}

function check_essential_files() {
  # Checks if files essential to start running the pipeline exist in the workdir
  # By default config.yaml and samples.tsv are considered essential files.

  if [ ! -d $WORKDIR ];then err "Folder $WORKDIR does not exist!"; fi
  for f in $ESSENTIAL_FILES; do
    fbn=$(basename $f)
    if [ ! -f $WORKDIR/config/$fbn ]; then err "Error: '${fbn}' file not found in $WORKDIR ... initialize first!";fi
  done
  for f in $ESSENTIAL_FOLDERS;do
    fbn=$(basename $f)
    if [ ! -d $WORKDIR/$fbn ]; then err "Error: '${fbn}' folder not found in $WORKDIR ... initialize first!";fi
  done
}

function reconfig(){

  # Rebuild config file and replace the config.yaml in the WORKDIR
  # this is only for dev purposes when new key-value pairs are being 
  # updated in the config file in PIPELINE_HOME

  check_essential_files
  _set_config
  echo "$WORKDIR/config.yaml has been updated!"

}

function runcheck(){
  # Check "job-essential" files and load required modules
  check_essential_files
  module load $PYTHON_VERSION
  module load $SNAKEMAKE_VERSION

}

function controlcheck(){
  # check controls are not listed in comparisons
  control_list=`awk '$3 ~ /Y/' ${WORKDIR}/config/samples.tsv | awk '{print $1}'`
  check1=`awk '{print $1}' ${WORKDIR}/config/contrasts.tsv`
  check2=`awk '{print $2}' ${WORKDIR}/config/contrasts.tsv`
  
  for sample_id in ${control_list[@]}; do
    if [[ $check1 =~ $sample_id || $check2 =~ $sample_id ]]; then 
      echo "Controls ($sample_id) cannot be listed in contrast.csv - update and re-run"
      exit 0
    fi
  done
}

function dryrun() {
  # check essential files, load modules and do Dry-run
  runcheck
  # can add controlcheck if needed

  if [ ! -d ${WORKDIR}/logs/dryrun/ ]; then mkdir ${WORKDIR}/logs/dryrun/; fi

  if [ -f ${WORKDIR}/dryrun.log ]; then
    modtime=$(stat ${WORKDIR}/dryrun.log |grep Modify|awk '{print $2,$3}'|awk -F"." '{print $1}'|sed "s/ //g"|sed "s/-//g"|sed "s/://g")
    mv ${WORKDIR}/dryrun.log ${WORKDIR}/logs/dryrun/dryrun.${modtime}.log
  fi

  run "--dry-run"

}

function unlock() {
  # check essential files, load modules and 
  # unlock the workdir if previous snakemake run ended abruptly

  runcheck
  run "--unlock"

}

function _exe_in_path() {

  name_of_exe=$1
  path_to_exe=$(which $name_of_exe 2>/dev/null)
 if [ ! -x "$path_to_exe" ] ; then
    err $path_to_exe NOT FOUND!
 fi

}

function set_singularity_binds(){

  # this functions tries find what folders to bind
  # "Biowulf specific"
  # assumes that config.yaml and samples.tsv in the WORKDIR are essential
  # files with the most uptodate information
  # required dos2unix in path
  _exe_in_path dos2unix
  echo "$PIPELINE_HOME" > ${WORKDIR}/tmp1
  echo "$WORKDIR" >> ${WORKDIR}/tmp1
  grep -o '\/.*' <(cat ${WORKDIR}/config.yaml ${WORKDIR}/samples.tsv)| \
    dos2unix | \
    tr '\t' '\n' | \
    grep -v ' \|\/\/' | \
    sort | \
    uniq >> ${WORKDIR}/tmp1
  grep gpfs ${WORKDIR}/tmp1|awk -F'/' -v OFS='/' '{print $1,$2,$3,$4,$5}' | \
    grep "[a-zA-Z0-9]" | \
    sort | uniq > ${WORKDIR}/tmp2
  grep -v gpfs ${WORKDIR}/tmp1|awk -F'/' -v OFS='/' '{print $1,$2,$3}' | \
    grep "[a-zA-Z0-9]" | \
    sort | uniq > ${WORKDIR}/tmp3
  while read a;do 
    readlink -f $a
  done < ${WORKDIR}/tmp3 | grep "[a-zA-Z0-9]"> ${WORKDIR}/tmp4
  binds=$(cat ${WORKDIR}/tmp2 ${WORKDIR}/tmp3 ${WORKDIR}/tmp4 | sort | uniq | tr '\n' ',')
  rm -f ${WORKDIR}/tmp?
  binds=$(echo $binds | awk '{print substr($1,1,length($1)-1)}')
  SINGULARITY_BINDS="-B $EXTRA_SINGULARITY_BINDS,$binds"

}

function dag() {
  runcheck
  module load graphviz
  snakemake -s $SNAKEFILE --configfile ${WORKDIR}/config/config.yaml --forceall --dag |dot -Teps > ${WORKDIR}/dag.eps
}

function testrun() {
  # Run for a test run - this is an example and should be edited, as needed
  check_essential_files
  sed -e "s/PIPELINE_HOME/${PIPELINE_HOME//\//\\/}/g" ${PIPELINE_HOME}/.test/samples.test.tsv > $WORKDIR/config/samples.tsv
  cp ${PIPELINE_HOME}/.test/contrasts.test.tsv $WORKDIR/config/contrasts.tsv
  check_essential_files
  dryrun
}

function printbinds(){
  # set the singularity binds and print them
  # singularity binds are /lscratch,/data/CCBR_Pipeliner,
  # plus paths deduced from config.yaml and samples.tsv using 
  # set_singularity binds function

  set_singularity_binds
  echo $SINGULARITY_BINDS

}

function runlocal() {
  # If the pipeline is fired up on an interactive node (with sinteractive), 
  # this function runs the pipeline

  runcheck
  set_singularity_binds
  if [ "$SLURM_JOB_ID" == "" ];then err "runlocal can only be done on an interactive node"; fi
  module load singularity
  run "local"

}

function runslurm() {

  # Submit the execution of the pipeline to the biowulf job scheduler (slurm)

  runcheck
  set_singularity_binds
  run "slurm"

}

function _get_file_modtime() {

# get the modification time for a file

  filename=$1
  modtime=$(stat $filename|grep Modify|awk '{print $2,$3}'|awk -F"." '{print $1}'|sed "s/ //g"|sed "s/-//g"|sed "s/://g")
  echo $modtime

}

function create_runinfo() {

# Create a runinfo.yaml file in the WORKDIR

  if [ -f ${WORKDIR}/runinfo.yaml ];then
    modtime=$(_get_file_modtime ${WORKDIR}/runinfo.yaml)
    mv ${WORKDIR}/runinfo.yaml ${WORKDIR}/runinfo.yaml.${modtime}
  fi
  echo "Pipeline Dir: $PIPELINE_HOME" > ${WORKDIR}/runinfo.yaml
  echo "Git Commit/Tag: $GIT_COMMIT_TAG" >> ${WORKDIR}/runinfo.yaml
  userlogin=$(whoami)
  username=$(finger $userlogin|grep ^Login|awk -F"Name: " '{print $2}')
  echo "Login: $userlogin" >> ${WORKDIR}/runinfo.yaml
  echo "Name: $username" >> ${WORKDIR}/runinfo.yaml
  g=$(groups)
  echo "Groups: $g" >> ${WORKDIR}/runinfo.yaml
  d=$(date)
  echo "Date/Time: $d" >> ${WORKDIR}/runinfo.yaml

}


function preruncleanup() {

  # Cleanup function to rename/move files related to older runs to prevent overwriting them.
  echo "Running..."

  # check initialization
  check_essential_files 

  cd $WORKDIR
  ## Archive previous run files
  if [ -f ${WORKDIR}/snakemake.log ];then 
    modtime=$(_get_file_modtime ${WORKDIR}/snakemake.log)
    mv ${WORKDIR}/snakemake.log ${WORKDIR}/stats/snakemake.${modtime}.log
    if [ -f ${WORKDIR}/snakemake.log.HPC_summary.txt ];then 
      mv ${WORKDIR}/snakemake.log.HPC_summary.txt ${WORKDIR}/stats/snakemake.${modtime}.log.HPC_summary.txt
    fi
    if [ -f ${WORKDIR}/snakemake.stats ];then 
      mv ${WORKDIR}/snakemake.stats ${WORKDIR}/stats/snakemake.${modtime}.stats
    fi
  fi
  nslurmouts=$(find ${WORKDIR} -maxdepth 1 -name "slurm-*.out" |wc -l)
  if [ "$nslurmouts" != "0" ];then
    for f in $(ls ${WORKDIR}/slurm-*.out);do mv ${f} ${WORKDIR}/logs/;done
  fi

  create_runinfo

}

function run() {
  # RUN function
  # argument1 can be:
  # 1. local or
  # 2. dryrun or
  # 3. unlock or
  # 4. slurm

  if [ "$1" == "local" ];then

  preruncleanup

  snakemake -s $SNAKEFILE \
  --directory $WORKDIR \
  --printshellcmds \
  --use-singularity \
  --singularity-args "$SINGULARITY_BINDS" \
  --use-envmodules \
  --latency-wait 120 \
  --configfile ${WORKDIR}/config.yaml \
  --cores all \
  --stats ${WORKDIR}/snakemake.stats \
  2>&1|tee ${WORKDIR}/snakemake.log

  if [ "$?" -eq "0" ];then
    snakemake -s $SNAKEFILE \
    --report ${WORKDIR}/runlocal_snakemake_report.html \
    --directory $WORKDIR \
    --configfile ${WORKDIR}/config.yaml 
  fi

  elif [ "$1" == "slurm" ];then
  
    preruncleanup
    # if QOS is other than "global" and is supplied in the cluster.json file then add " --qos={cluster.qos}" to the 
    # snakemake command below
  cat > ${WORKDIR}/submit_script.sbatch << EOF
#!/bin/bash
#SBATCH --job-name="CCBRPipeline"
#SBATCH --mem=10g
#SBATCH --partition="norm"
#SBATCH --time=96:00:00
#SBATCH --cpus-per-task=2

module load $PYTHON_VERSION
module load $SNAKEMAKE_VERSION
module load singularity

cd \$SLURM_SUBMIT_DIR

snakemake -s $SNAKEFILE \
--directory $WORKDIR \
--use-singularity \
--singularity-args "$SINGULARITY_BINDS" \
--use-envmodules \
--printshellcmds \
--latency-wait 120 \
--configfile ${WORKDIR}/config.yaml \
--cluster-config ${PIPELINE_HOME}/resources/cluster.yaml \
--cluster "sbatch --gres {cluster.gres} --cpus-per-task {cluster.threads} -p {cluster.partition} -t {cluster.time} --mem {cluster.mem} --job-name {cluster.name} --output {cluster.output} --error {cluster.error}" \
-j 500 \
--rerun-incomplete \
--keep-going \
--stats ${WORKDIR}/snakemake.stats \
2>&1|tee ${WORKDIR}/snakemake.log

if [ "\$?" -eq "0" ];then
  snakemake -s $SNAKEFILE \
  --directory $WORKDIR \
  --report ${WORKDIR}/runslurm_snakemake_report.html \
  --configfile ${WORKDIR}/config.yaml 
fi

bash <(curl https://raw.githubusercontent.com/CCBR/Tools/master/Biowulf/gather_cluster_stats.sh 2>/dev/null) ${WORKDIR}/snakemake.log > ${WORKDIR}/snakemake.log.HPC_summary.txt

EOF

  sbatch ${WORKDIR}/submit_script.sbatch

  else # for unlock and dryrun 
    snakemake $1 -s $SNAKEFILE \
    --directory $WORKDIR \
    --use-envmodules \
    --printshellcmds \
    --latency-wait 120 \
    --configfile ${WORKDIR}/config.yaml \
    --cluster-config ${PIPELINE_HOME}/config/cluster.yaml \
    --cluster "sbatch --gres {cluster.gres} --cpus-per-task {cluster.threads} -p {cluster.partition} -t {cluster.time} --mem {cluster.mem} --job-name {cluster.name} --output {cluster.output} --error {cluster.error}" \
    -j 500 \
    --rerun-incomplete \
    --keep-going \
    --stats ${WORKDIR}/snakemake.stats

  fi

}

function reset() {
  # Delete the workdir and re-initialize it

  echo "Working Dir: $WORKDIR"
  if [ ! -d $WORKDIR ];then err "Folder $WORKDIR does not exist!";fi
  echo "Deleting $WORKDIR"
  rm -rf $WORKDIR
  echo "Re-Initializing $WORKDIR"
  init

}

function main(){
  # Main function which parses all arguments

  if [ $# -eq 0 ]; then usage && exit 1; fi

  for i in "$@"; do
  case $i in
      -m=*|--runmode=*)
        RUNMODE="${i#*=}"
      ;;
      -w=*|--workdir=*)
        WORKDIR="${i#*=}"
      ;;
      *)
        err "Unknown argument!"    # unknown option
      ;;
  esac
  done
  WORKDIR=$(readlink -f "$WORKDIR")
  echo "Working Dir: $WORKDIR"

  case $RUNMODE in
    init) init && exit 0;;
    dryrun) dryrun && exit 0;;
    unlock) unlock && exit 0;;
    run) runslurm && exit 0;;
    runlocal) runlocal && exit 0;;
    reset) reset && exit 0;;
    dry) dryrun && exit 0;;                      # hidden option
    local) runlocal && exit 0;;                  # hidden option
    reconfig) reconfig && exit 0;;               # hidden option for debugging
    printbinds) printbinds && exit 0;;           # hidden option
    *) err "Unknown RUNMODE \"$RUNMODE\"";;
  esac

}

# call the main function

main "$@"
