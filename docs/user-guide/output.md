This should include all pertitant information about output files, including extensions that differentiate files. An example is provided below.

# 4. Expected Outputs

The following directories are created under the WORKDIR/results directory:

- alignment_stats: this directory include information on the alignment of each sample
- peaks: this directory contains a sub-directory that relates to the quality threshold used.
    - quality threshold
        - contrasts: this directory includes the contrasts for each line listed in the contrast manifest
        - peak_caller: this directory includes all peak calls from each peak_caller (SEACR, MACS2, GOPEAKS) for each sample
            - annotation
                - go_enrichment: this directory includes gene set enrichment pathway predictions
                - homer: this directory includes the annotation output from HOMER
                - rose: this directory includes the annotation output from ROSE

```
├── alignment_stats
├── bam
├── peaks
│   ├── 0.05
│   │   ├── contrasts
│   │   │   ├── contrast_id1.dedup_status
│   │   │   └── contrast_id2.dedup_status
│   │   ├── gopeaks
│   │   │   ├── annotation
│   │   │   │   ├── go_enrichment
│   │   │   │   │   ├── contrast_id1.dedup_status.go_enrichment_tables
│   │   │   │   │   └── contrast_id2.dedup_status.go_enrichment_html_report
│   │   │   │   ├── homer
│   │   │   │   │   ├── replicate_id1_vs_control_id.dedup_status.gopeaks_broad.motifs
│   │   │   │   │   │   ├── homerResults
│   │   │   │   │   │   └── knownResults
│   │   │   │   │   ├── replicate_id1_vs_control_id.dedup_status.gopeaks_narrow.motifs
│   │   │   │   │   │   ├── homerResults
│   │   │   │   │   │   └── knownResults
│   │   │   │   │   ├── replicate_id2_vs_control_id.dedup_status.gopeaks_broad.motifs
│   │   │   │   │   │   ├── homerResults
│   │   │   │   │   │   └── knownResults
│   │   │   │   │   ├── replicate_id2_vs_control_id.dedup_status.gopeaks_narrow.motifs
│   │   │   │   │   │   ├── homerResults
│   │   │   │   │   │   └── knownResults
│   │   │   │   └── rose
│   │   │   │       ├── replicate_id1_vs_control_id.dedup_status.gopeaks_broad.12500
│   │   │   │       ├── replicate_id1_vs_control_id.dedup_status.gopeaks_narrow.12500
│   │   │   │       ├── replicate_id2_vs_control_id.dedup_status.dedup.gopeaks_broad.12500
│   │   │   │       ├── replicate_id2_vs_control_id.dedup_status.dedup.gopeaks_narrow.12500
│   │   │   └── peak_output
│   │   ├── macs2
│   │   │   ├── annotation
│   │   │   │   ├── go_enrichment
│   │   │   │   │   ├── contrast_id1.dedup_status.go_enrichment_tables
│   │   │   │   │   └── contrast_id2.dedup_status.go_enrichment_html_report
│   │   │   │   ├── homer
│   │   │   │   │   ├── replicate_id1_vs_control_id.dedup_status.macs2_narrow.motifs
│   │   │   │   │   │   ├── homerResults
│   │   │   │   │   │   └── knownResults
│   │   │   │   │   ├── replicate_id1_vs_control_id.dedup_status.macs2_broad.motifs
│   │   │   │   │   │   ├── homerResults
│   │   │   │   │   │   └── knownResults
│   │   │   │   │   ├── replicate_id2_vs_control_id.dedup_status.macs2_narrow.motifs
│   │   │   │   │   │   ├── homerResults
│   │   │   │   │   │   └── knownResults
│   │   │   │   │   ├── replicate_id2_vs_control_id.dedup_status.macs2_broad.motifs
│   │   │   │   │   │   ├── homerResults
│   │   │   │   │   │   └── knownResults
│   │   │   │   └── rose
│   │   │   │       ├── replicate_id1_vs_control_id.dedup_status.macs2_broad.12500
│   │   │   │       ├── replicate_id1_vs_control_id.dedup_status.macs2_narrow.12500
│   │   │   │       ├── replicate_id2_vs_control_id.dedup_status.macs2_broad.12500
│   │   │   │       ├── replicate_id2_vs_control_id.dedup_status.macs2_narrow.12500
│   │   │   └── peak_output
```
