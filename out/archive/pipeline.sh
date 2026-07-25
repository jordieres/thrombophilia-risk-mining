#! /bin/bash
#
source ../vpy/bin/activate
#
python src/cli.py --data data/patD.parquet --experiment clustering --clustering-max-samples 20000  --clustering-metric manhattan
#
python src/cli.py --data data/patD.parquet --experiment clustering --clustering-max-samples 20000  --clustering-metric cosine
#
python src/cli.py  --data data/patD.parquet   --experiment score   --score-feature-strategy compare   --score-max-samples 2500   --score-max-feature-cardinality 12   --score-numeric-bins 4   --score-cv-splits 4   --score-min-sensitivity 0.90   --score-benchmark-model both   --score-top-features 10   --score-xgboost-estimators 80   --output-dir out
#
python src/cli.py  --data data/patD.parquet   --experiment score   --score-feature-strategy compare   --score-max-samples 2500   --score-max-feature-cardinality 12   --score-numeric-bins 4   --score-cv-splits 4   --score-min-sensitivity 0.90   --score-benchmark-model both   --score-top-features 10   --score-xgboost-estimators 80   --output-dir out
#
python src/cli.py  --data data/patD.parquet   --experiment score   --score-feature-strategy compare   --score-max-samples 2500   --score-max-feature-cardinality 12   --score-numeric-bins 4   --score-cv-splits 4   --score-min-sensitivity 0.90   --score-benchmark-model both   --score-top-features 10   --score-xgboost-estimators 80   --output-dir out
#
python src/cli.py  --data data/patD.parquet   --experiment score   --score-feature-strategy compare   --score-max-samples 2500   --score-max-feature-cardinality 12   --score-numeric-bins 4   --score-cv-splits 4   --score-min-sensitivity 0.90   --score-benchmark-model both   --score-top-features 10   --score-xgboost-estimators 80   --output-dir out
#
python src/cli.py  --data data/patD.parquet   --experiment score   --score-feature-strategy compare   --score-max-samples 22500   --score-max-feature-cardinality 22   --score-numeric-bins 6   --score-cv-splits 5   --score-min-sensitivity 0.90   --score-benchmark-model both   --score-top-features 10   --score-xgboost-estimators 80   --output-dir out
#
python src/cli.py --data data/patD.parquet --experiment edas --edas-column ddvalmcg --edas-analysis histogram --edas-bins 12
#
python src/cli.py --data data/patD.parquet --experiment edas --edas-column ddvalmcg --edas-analysis histogram --edas-bins 25
#
python src/cli.py  --data data/patD.parquet  --experiment edas  --edas-column ddvalmcg  --edas-analysis histogram  --edas-bins 20  --edas-range-min 0  --edas-range-max 50000
#
python src/cli.py  --data data/patD.parquet  --experiment edas  --edas-column ddvalmcg  --edas-analysis histogram  --edas-bins 20  --edas-range-min 0  --edas-range-max 500
#
vi color_rules.json
#
python src/cli.py   --data data/patD_slim.parquet   --experiment clustering   --clustering-max-samples 22000   --clustering-metric cosine   --clustering-n-clusters 4   --clustering-n-neighbors 25   --clustering-min-dist 0.05   --clustering-color-rules-json color_rules.json   --output-dir out/umap_cosine_alt_color
#
python src/cli.py   --data data/patD_slim.parquet   --experiment clustering   --clustering-max-samples 22000   --clustering-metric cosine   --clustering-n-clusters 4   --clustering-n-neighbors 25   --clustering-min-dist 0.05   --clustering-color-rules-json color_rules.json   --output-dir out/umap_cosine_alt_color
#
python src/cli.py   --data data/patD.parquet   --experiment categorical_association   --association-target-column var161   --association-max-samples 30000   --association-max-columns 20   --association-top-k 25   --output-dir out/var161_assoc
#
python src/cli.py   --data data/patD.parquet   --experiment association_explorer   --association-rules-max-samples 22000   --association-rules-min-support 0.01   --association-rules-min-confidence 0.40   --association-rules-min-lift 1.00   --association-rules-max-feature-cardinality 12   --association-rules-max-features 24   --association-rules-max-rule-size 3   --association-rules-top-k 50   --association-rules-sort-metric leverage   --association-rules-filter-column var161   --association-rules-filter-side either   --output-dir out/var161_rules
#
python src/cli.py  --data data/patD.parquet --experiment contrast --contrast-target-column var161 --contrast-max-samples 30000 --contrast-min-support 0.02 --contrast-min-confidence 0.35 --contrast-max-feature-cardinality 22 --contrast-max-features 60 --contrast-max-rule-size 9 --contrast-top-k-per-outcome 25 --contrast-workers 4 --output-dir out/var161_contrast
#
python src/cli.py   --data data/patD.parquet   --experiment contrast   --contrast-target-column var161   --contrast-target-valid-labels Sí No   --contrast-max-samples 12000   --contrast-min-support 0.05   --contrast-min-confidence 0.40   --contrast-max-feature-cardinality 12   --contrast-max-features 25   --contrast-max-rule-size 3   --contrast-top-k-per-outcome 20   --contrast-workers 1   --output-dir out/var161_contrast_light
#
python src/cli.py   --data data/patD.parquet   --experiment contrast   --contrast-target-column var161   --contrast-target-valid-labels Sí No   --contrast-max-samples 30000   --contrast-min-support 0.05   --contrast-min-confidence 0.40   --contrast-max-feature-cardinality 12   --contrast-max-features 25   --contrast-max-rule-size 3   --contrast-top-k-per-outcome 20   --contrast-workers 1   --output-dir out/var161_contrast_light
#
# var161 analysis
#
python src/patd_spec_tool.py   --input-parquet data/patD.parquet   --spec-xlsx "/tmp/varibeles explained.xlsx"   --target-columns var161   --filter-column var161   --filter-allowed-values Sí No   --output-parquet data/patD_var161.parquet   --report-json out/patD_var161_validation.json
#
python src/cli.py  --data data/patD_var161.parquet --experiment permutation  --permutation-target-column var161  --permutation-positive-label Sí  --permutation-negative-label No  --permutation-max-samples 31000  --permutation-top-k 30  --output-dir out/var161_permutation
#
python src/cli.py  --data data/patD_var161.parquet --experiment permutation  --permutation-target-column var161  --permutation-positive-label Sí  --permutation-negative-label No  --permutation-max-samples 31000  --output-dir out/var161_permutation
#
python src/cli.py   --data data/patD_var161.parquet   --experiment score   --score-target-column var161   --score-positive-label Sí   --score-negative-label No   --score-feature-strategy compare   --score-max-samples 31000   --score-max-feature-cardinality 18   --score-numeric-bins 8   --score-cv-splits 5   --score-min-sensitivity 0.90   --score-benchmark-model both   --score-top-features 10   --score-xgboost-estimators 60   --output-dir out/var161_score
#
# andujak2 variables
#
python src/patd_spec_tool.py   --input-parquet data/patD.parquet   --spec-xlsx "/tmp/varibeles explained.xlsx"   --target-columns andujak2   --filter-column andujak2   --filter-allowed-values Sí No   --output-parquet data/patD_andujak2.parquet   --report-json out/patD_andujak2_validation.json
#
python src/cli.py   --data data/patD_andujak2.parquet   --experiment categorical_association   --association-target-column andujak2   --association-target-valid-labels Sí No   --association-max-samples 2160   --association-max-columns 20   --association-top-k 25   --output-dir out/andujak2_assoc
#
python src/cli.py   --data data/patD_andujak2.parquet   --experiment permutation   --permutation-target-column andujak2   --permutation-positive-label Sí   --permutation-negative-label No   --permutation-max-samples 2160   --permutation-max-splits 3   --permutation-repeats 3   --permutation-estimators 40   --output-dir out/andujak2_permutation
#
python src/cli.py  --data data/patD_andujak2.parquet  --experiment score  --score-target-column andujak2  --score-positive-label Sí  --score-negative-label No  --score-feature-strategy compare  --score-max-samples 2160  --score-max-feature-cardinality 18  --score-numeric-bins 6  --score-cv-splits 3  --score-min-sensitivity 0.90  --score-benchmark-model both  --score-top-features 8  --score-xgboost-estimators 40 --output-dir out/andujak2_score
#
python src/cli.py   --data data/patD_andujak2.parquet   --experiment association_explorer   --association-rules-target-column andujak2   --association-rules-target-valid-labels Sí No   --association-rules-filter-column andujak2   --association-rules-filter-side either   --association-rules-max-samples 2160   --association-rules-min-support 0.03   --association-rules-min-confidence 0.40   --association-rules-min-lift 1.00   --association-rules-max-feature-cardinality 12   --association-rules-max-features 20   --association-rules-max-rule-size 3   --association-rules-top-k 40   --association-rules-sort-metric leverage   --output-dir out/andujak2_rules
#
# var158 analysis
#
python src/patd_spec_tool.py   --input-parquet data/patD.parquet   --spec-xlsx "/tmp/varibeles explained.xlsx"   --target-columns var158   --filter-column var158   --filter-allowed-values Sí No   --output-parquet data/patD_var158.parquet   --report-json out/patD_var158_validation.json
#
python src/cli.py   --data data/patD_var158.parquet   --experiment categorical_association   --association-target-column var158   --association-target-valid-labels Sí No   --association-max-samples 30000   --association-max-columns 20   --association-top-k 25   --output-dir out/var158_assoc
#
python src/cli.py   --data data/patD_var158.parquet   --experiment association_explorer   --association-rules-target-column var158   --association-rules-target-valid-labels Sí No   --association-rules-filter-column var158   --association-rules-filter-side either   --association-rules-max-samples 30800   --association-rules-min-support 0.03   --association-rules-min-confidence 0.40   --association-rules-min-lift 1.00   --association-rules-max-feature-cardinality 12   --association-rules-max-features 20   --association-rules-max-rule-size 3   --association-rules-top-k 40   --association-rules-sort-metric leverage   --output-dir out/var158_rules
#
python src/cli.py  --data data/patD_var158.parquet  --experiment score  --score-target-column var158  --score-positive-label Sí  --score-negative-label No  --score-feature-strategy compare  --score-max-samples 30800  --score-max-feature-cardinality 18  --score-numeric-bins 6  --score-cv-splits 5  --score-min-sensitivity 0.90  --score-benchmark-model both  --score-top-features 8  --score-xgboost-estimators 40 --output-dir out/var158_score
