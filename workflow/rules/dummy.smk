# example smk file
rule dummy:
    input:
    output:
    envmodules:
        TOOLS["cutadapt"]["version"]
    container: config["masterdocker"]    
    threads: getthreads("dummy")
    shell:"""
set -e -x -o pipefail
if [ -w "/lscratch/${{SLURM_JOB_ID}}" ];then 
    tmpdir="/lscratch/${{SLURM_JOB_ID}}"
else 
    tmpdir=$(mktemp -d -p /dev/shm)
fi
"""