def get_input_fastqs(wildcards):
    d = dict()
    d["R1"] = replicateName2R1[wildcards.replicate]
    d["R2"] = replicateName2R2[wildcards.replicate]
    return d

# example smk file
rule dummy:
    input:
        R1 = rules.trim.output.R1,
    output:
        bam=join(RESULTSDIR,"bam","raw","{replicate}.bam"),
    envmodules:
        TOOLS["cutadapt"]
    container: config["masterdocker"]    
    threads: getthreads("dummy")
    shell:
        """
        set -e -x -o pipefail
        if [ -w "/lscratch/${{SLURM_JOB_ID}}" ];then 
            tmpdir="/lscratch/${{SLURM_JOB_ID}}"
        else 
            tmpdir=$(mktemp -d -p /dev/shm)
        fi
        """