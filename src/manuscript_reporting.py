"""English manuscript sections, coauthor replies, and standalone research figures.

Reports consume completed reanalysis CSV/JSON files and reuse published figures
when local patient predictions are unavailable. No old AUC,
threshold, point card, or denominator is copied from exploratory output. Pandoc
and matplotlib are optional export dependencies; Markdown/CSV remain canonical.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET
import shutil
import subprocess

import numpy as np
import pandas as pd

from manuscript_cohort import OUTCOMES, LABELS, NUMERIC
from manuscript_artifacts import artifact_inventory


def table(frame: pd.DataFrame, columns: list[str] | None = None, digits: int = 3) -> str:
    """Render a portable Markdown table without an optional tabulate dependency."""
    d=frame[columns].copy() if columns else frame.copy()
    def cell(value):
        if pd.isna(value):return 'Not estimable'
        if isinstance(value,(float,np.floating)):return f'{value:.{digits}f}'
        return str(value).replace('|','/').replace('\n',' ')
    return '\n'.join(['| '+' | '.join(d.columns)+' |','| '+' | '.join(['---']*len(d.columns))+' |']+
                     ['| '+' | '.join(cell(v) for v in row)+' |' for row in d.itertuples(index=False,name=None)])


def export_word(markdown: Path) -> bool:
    """Create a shareable DOCX when Pandoc is available; preserve the Markdown source."""
    if not shutil.which('pandoc'):return False
    subprocess.run(['pandoc',str(markdown),'-o',str(markdown.with_suffix('.docx'))],check=True)
    return True


def display_performance(metrics: pd.DataFrame) -> pd.DataFrame:
    """Format clinically interpretable columns while retaining exact CSV precision."""
    rows=[]
    for r in metrics.itertuples():
        ci=f'{r.auc:.3f} [{r.auc_lower:.3f}, {r.auc_upper:.3f}]' if np.isfinite(r.auc) else 'Not estimable'
        rows.append(dict(Outcome=r.label,Model=r.model,N=r.n,Positive=r.positive_n,AUC_95CI=ci,
            Sensitivity=f'{100*r.sensitivity:.1f}%',Specificity=f'{100*r.specificity:.1f}%',
            PPV=f'{100*r.ppv:.1f}%' if np.isfinite(r.ppv) else 'Undefined',
            NPV=f'{100*r.npv:.1f}%' if np.isfinite(r.npv) else 'Undefined',
            Avoided_per_1000=round(r.tests_avoided_per_1000,1),Missed_per_1000=round(r.missed_positive_per_1000,1)))
    return pd.DataFrame(rows)


def concise_baseline(csv: Path) -> pd.DataFrame:
    """Format the principal manuscript variables with observed-denominator percentages."""
    d=pd.read_csv(csv);rows=[]
    fields={'edad':'continuous','sexo':'Female','hip_art':'Yes','diabetes':'Yes','fum_act':'Yes',
            'fr_cance':'Yes','fr_inmov':'Yes','fr_tvp_a':'Yes','fr_antfa':'Yes'}
    for col,category in fields.items():
        group=d[(d.variable==col)&(d.category==category)]
        if group.empty:continue
        r=group.iloc[0]
        vals=[]
        for prefix in ['first','second']:
            if category=='continuous':
                val=f"{r[prefix+'_mean']:.1f} ± {r[prefix+'_sd']:.1f}; median {r[prefix+'_median']:.0f} [{r[prefix+'_q1']:.0f}–{r[prefix+'_q3']:.0f}]"
            else:val=f"{int(r[prefix+'_count'])}/{int(r[prefix+'_observed_n'])} ({r[prefix+'_percent']:.1f}%)"
            vals.append(val)
        rows.append(dict(Variable=r.label,First_group=vals[0],Second_group=vals[1],
                         Missing_first=int(r.first_missing_n),Missing_second=int(r.second_missing_n),
                         SMD=r.standardized_difference,p_value=r.p_value))
    return pd.DataFrame(rows)


def outcome_policy_text(config: dict) -> str:
    """State the actual outcome interpretation, including the JAK2 exception."""
    if config.get('outcome_policy', 'explicit-results') == 'routine-panel':
        return ('According to the study investigators’ routine-panel interpretation clarified on '
                '8 September 2026, globally tested patients are assumed to have had FVL, '
                'prothrombin G20210A, APS, protein C, protein S and antithrombin assessed. '
                'Missing results for those six subtypes were therefore interpreted as negative, '
                'only when ana_dura was explicitly positive or negative. JAK2 was not considered '
                'routine: its missing results remained missing and only explicit positive/negative '
                'JAK2 results were eligible. Source labels were preserved and all interpreted '
                'negatives were counted separately. This is an explicit clinical registry-coding '
                'assumption, not patient-level laboratory adjudication. Nonbinary labels other '
                'than missing were not converted to negative.')
    return ('This explicit-results sensitivity analysis requires a recorded positive or negative '
            'subtype result within globally tested patients. Missing subtype outcomes remain '
            'excluded, including JAK2. It intentionally does not apply the investigators’ '
            'routine-panel missing-as-negative interpretation.')


def methods_text(config: dict) -> str:
    """Describe the implemented workflow and its unavoidable extract-level limitations."""
    return f'''The full registry was used for descriptive comparisons. Documented thrombophilia testing was defined by a positive or negative global testing label. Explicitly untested records and records with unknown global testing status were combined for the descriptive not-tested/unknown group, with their component counts reported separately. Predictive analyses required documented global testing. {outcome_policy_text(config)} Patients with explicitly documented prior carrier status or known APS were excluded from predictive analyses. Unknown prior-carrier status was not equated with confirmed absence. The extract contains no independent assay-performed flag; consequently, this operational definition cannot independently establish laboratory testing for every subtype-negative record.

Only an explicit allowlist of index-event demographic, presentation, history and laboratory variables was eligible. Thrombophilia results, global testing status, previously known APS, quantitative D-dimer, follow-up events and identifiers were excluded as predictors. Statin treatment (trat_est) and recent hormone exposure (fr_estro) were treated as distinct variables. Numeric quality failures were set to missing without deleting registry rows. Fixed clinical categories replaced sample-derived quantiles: age <50/50–69/≥70 years; hemoglobin <12/≥12 g/dL; platelets <144/144–400/>400 ×10^9/L; leukocytes <4/4–11/>11 ×10^9/L; and the additional categories in Supplementary Table S1. Categorical D-dimer used the recorded result; explicitly not performed and unknown remained distinct. Missing history was not assumed absent. Quantitative D-dimer was not used or converted to an assay-independent threshold.

Development used diagnoses through {config['cutoff_year']}; diagnoses from {config['cutoff_year']+1} onward were held out. For each outcome, nonconstant candidate variables with no more than {100*config['max_missing']:.0f}% missingness in development were retained for the principal comparison. This outcome-blind candidate-availability definition was fixed using the development covariate distribution before internal cross-validation. Complete cases for that candidate set formed the common population for LASSO, integer-score and XGBoost comparisons; it is stricter than complete cases for only the eventual nonzero score components. Patient losses and included-versus-excluded characteristics were reported. A separate XGBoost sensitivity analysis retained incomplete records and all nonconstant allowlisted predictors. It differs in both population and predictor set and is not a pure isolated comparison of imputation methods.

Within each training fold, candidate categorical predictors were screened by the likelihood-ratio test comparing a univariable categorical logistic model with intercept only, using p<0.10. The equivalent contingency-table G test was used to avoid numerical separation of univariable coefficients; these asymptotic screening p-values were exploratory, not confirmatory inference. Retained variables were one-hot encoded using training-only category levels and entered into L1-regularized logistic regression. The inverse regularization parameter C was selected from {"0.01 and 0.1 (compact test grid)" if config["compact"] else "0.01, 0.1, 1 and 10"} by inner cross-validation AUC. No class weighting was applied. If screening or regularization selected no components, an intercept-only model was retained and its lack of discrimination was reported.

Integer points preserved coefficient signs: each nonzero coefficient was divided by the smallest nonzero absolute coefficient and rounded. Higher signed totals corresponded to greater predicted positivity. A nonnegative-slope logistic mapping fitted on training point totals converted the actual simplified score into a probability; this mapping was distinct from the full logistic model. Inner-validation probabilities selected a threshold targeting sensitivity ≥{100*config['min_sensitivity']:.0f}%, maximizing specificity subject to this requirement. Fold-specific cards were mapped to probabilities before pooling; pooled calibrated-score AUC and mean within-fold raw-score AUC were reported separately. The final development card and its probability/point thresholds were fixed before temporal evaluation. A composite-only guided exploratory comparison used a prespecified subset of clinical descriptors from the previous manuscript, not rules selected on held-out outcomes.

XGBoost used dense one-hot representations, observed zeros and NaN blocks for missing or unseen source categories. {"Two compact test" if config["compact"] else "Four declared"} hyperparameter configurations varied tree depth, learning rate, subsampling, column sampling, regularization and tree number; model selection used inner-fold AUC. The exact search is archived in the run manifest. Internal validation used {config['outer_splits']} stratified outer folds and {config['inner_splits']} inner folds, reduced only if minority counts required it. Screening, coefficient fitting, category vocabularies, calibration and threshold selection were refitted within training partitions. The outer validation outcomes did not select thresholds. Observed validation sensitivity could therefore be below the targeted training sensitivity.

AUC, TP/FP/TN/FN, sensitivity, specificity, PPV, NPV, likelihood ratios, Brier score and log loss were reported. Tests avoided and positive results missed per 1,000 were derived from the same confusion matrix. Calibration used the actual held-out probability of each model, ten fixed-width bins, unweighted mean absolute calibration error (MACE) across occupied bins and count-weighted error (ECE). Proportion intervals used the Wilson method. AUC intervals used {config['bootstrap']} stratified resamples of fixed held-out predictions and are conditional descriptive intervals; they do not include uncertainty from repeating model selection. Undefined quantities were not replaced by zero. Temporal models, vocabularies and operating thresholds were learned only from development.

Testing-by-sex probabilities were additionally represented by the maximum-likelihood conditional probability table of a prespecified Sex → global testing status Bayesian network; this is a descriptive factorization of observed frequencies, not causal inference. Negative-result association rules used FP-Growth over prespecified clinical descriptors in the eligible composite cohort, joint support ≥1%, confidence ≥80%, lift ≥1, and at most three antecedents. Joint rule support and antecedent support were reported separately. These rules were exploratory and were not interpreted as validated triage performance.

Laboratory confirmation of persistent APS, assay timing relative to anticoagulation, and independent assay-performed indicators were unavailable in this extract. Country/centre validation and causal explanations of sex differences or recurrence were not supported. Registry-coded APS should not be described as universally based on a single test merely because repeat-test information was unavailable.'''


def generate_figures(output: Path) -> list[str]:
    """Export standalone PNG/SVG ROC, calibration, score distribution and cohort flow."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from sklearn.metrics import roc_curve
    figure_dir=output/'figures';figure_dir.mkdir(exist_ok=True)
    created=[]
    for o in OUTCOMES:
        path=output/o.column/'predictions.parquet'
        if not path.exists():
            if not (output/o.column/'metrics.csv').exists():
                continue
            cached=[figure_dir/f'{o.column}_validation.{ext}' for ext in ['png','svg']]
            if not all(f.is_file() for f in cached):
                raise FileNotFoundError(f'{o.column}: local predictions or both published aggregate figures are required to generate reports.')
            created.extend(str(f.relative_to(output)) for f in cached)
            continue
        d=pd.read_parquet(path);primary=d.query("analysis=='primary_complete_case' and validation=='nested_cv'")
        fig,axes=plt.subplots(1,3,figsize=(15,4.3),constrained_layout=True)
        for model,g in primary.groupby('model'):
            if g.y_true.nunique()==2:
                fpr,tpr,_=roc_curve(g.y_true,g.probability)
                from sklearn.metrics import roc_auc_score
                axes[0].plot(fpr,tpr,label=f'{model} ({roc_auc_score(g.y_true,g.probability):.3f})')
            from manuscript_models import calibration_bins
            bins=calibration_bins(g)
            axes[1].plot(bins.predicted,bins.observed,'o-',label=model)
        for ax in axes[:2]:ax.plot([0,1],[0,1],'k--',lw=.7);ax.set_xlim(0,1);ax.set_ylim(0,1)
        axes[0].set(xlabel='False positive rate',ylabel='Sensitivity',title='Nested validation ROC');axes[0].legend(fontsize=7)
        axes[1].set(xlabel='Predicted probability',ylabel='Observed positivity',title='Held-out calibration')
        integer=primary[primary.model=='Automatic integer score']
        for y,label in [(0,'Negative'),(1,'Positive')]:
            p=integer.loc[integer.y_true==y,'probability']
            axes[2].hist(p,bins=np.linspace(0,1,21),alpha=.5,density=True,label=label)
        axes[2].set(xlabel='Calibrated integer-score probability',ylabel='Density',title='Held-out score distributions');axes[2].legend(fontsize=8)
        fig.suptitle(o.label)
        for ext in ['png','svg']:
            target=figure_dir/f'{o.column}_validation.{ext}';fig.savefig(target,dpi=180);created.append(str(target.relative_to(output)))
        plt.close(fig)
    flow=json.loads((output/'registry_flow.json').read_text());cohorts=pd.read_csv(output/'model_cohort_flow.csv')
    fig,ax=plt.subplots(figsize=(12,7));ax.axis('off')
    def box(x,y,text):ax.text(x,y,text,ha='center',va='center',bbox=dict(boxstyle='round,pad=.6',fc='#eef3f8',ec='#34495e'),fontsize=10)
    box(.5,.93,f"Full registry: {flow['registry_n']:,}")
    box(.22,.71,f"Not tested / unknown: {flow['not_tested_or_unknown_n']:,}\nExplicit: {flow['explicitly_not_tested_n']:,}; unknown: {flow['unknown_testing_n']:,}")
    box(.73,.71,f"Documented testing: {flow['tested_n']:,}\nPositive: {flow['positive_n']:,}; negative: {flow['negative_n']:,}")
    box(.73,.49,f"Exclude known pre-existing thrombophilia: {flow['known_thrombophilia_tested_n']:,}\nApply declared outcome interpretation")
    text='Outcome: eligible → development complete / temporal complete\n'+'\n'.join(f'{r.label}: {r.eligible_n:,} → {r.development_complete_n:,} / {r.temporal_complete_n:,}' for r in cohorts.itertuples())
    box(.5,.16,text)
    for a,b in [((.5,.87),(.22,.79)),((.5,.87),(.73,.79)),((.73,.63),(.73,.57)),((.73,.41),(.5,.34))]:ax.annotate('',xy=b,xytext=a,arrowprops=dict(arrowstyle='->'))
    for ext in ['png','svg']:
        target=figure_dir/f'cohort_flow.{ext}';fig.savefig(target,dpi=180,bbox_inches='tight');created.append(str(target.relative_to(output)))
    plt.close(fig)
    return created


def generate_reports(output: Path) -> None:
    """Build a complete English response pack directly from the current run outputs."""
    manifest=json.loads((output/'run_manifest.json').read_text());config=manifest['config']
    metrics=pd.read_csv(output/'all_model_metrics.csv');flows=pd.read_csv(output/'model_cohort_flow.csv')
    registry=json.loads((output/'registry_flow.json').read_text());den=pd.read_csv(output/'supplement_outcome_denominators.csv')
    sex=pd.read_csv(output/'sex_testing_yield.csv');assoc=json.loads((output/'association_config.json').read_text())
    primary=metrics.query("analysis=='primary_complete_case' and validation=='nested_cv'")
    temporal=metrics.query("analysis=='primary_complete_case' and validation=='temporal_holdout'")
    native=metrics.query("analysis=='sensitivity_native_missing' and validation=='nested_cv'")
    # Saturated ML CPD for the declared two-node descriptive Bayesian network.
    cpd=[]
    for r in sex.itertuples():
        for state,n in [('Positive',r.positive_n),('Negative',r.tested_n-r.positive_n),('Not tested / unknown',r.n-r.tested_n)]:
            cpd.append(dict(sex=r.sex,status=state,n=n,sex_n=r.n,conditional_probability=n/r.n))
    pd.DataFrame(cpd).to_csv(output/'testing_pattern_bayesian_cpd.csv',index=False)
    figures=generate_figures(output)
    method=methods_text(config)
    policy_text=outcome_policy_text(config)
    principal = config.get('outcome_policy', 'explicit-results') == 'routine-panel'
    policy_role = ('This routine-panel interpretation is the principal paper analysis.' if principal
                   else 'This explicit-results interpretation is an alternative policy analysis.')
    sections=['# Replacement manuscript sections — recalculated analysis','',
        'These sections and tables supersede the numerical statements in the supplied draft. They describe the executed analysis, not a reproduction of the old AUCs. JAK2 remains descriptive. All confidence intervals are conditional on the stored predictions.','',
        '## Outcome interpretation','',policy_text,'','## Methods','',method,'','## Results','',
        f"The registry included {registry['registry_n']:,} unique patients. Global thrombophilia testing was documented in {registry['tested_n']:,} ({100*registry['tested_n']/registry['registry_n']:.1f}%), including {registry['positive_n']:,} positive and {registry['negative_n']:,} negative evaluations. There were {registry['explicitly_not_tested_n']:,} explicitly untested records and {registry['unknown_testing_n']:,} records with unknown global testing status. Predictive eligibility excluded {registry['known_thrombophilia_tested_n']:,} tested patients with explicitly known pre-existing thrombophilia/APS.",
        '',table(flows,['label','eligible_n','eligible_positive_n','candidate_n','development_complete_n','temporal_complete_n','missing_excluded_n']),
        '', 'The complete-case losses materially limit representativeness. Subtype denominators follow the declared outcome policy within globally tested patients. For the routine-panel analysis, interpreted negatives are included for the six routine tests but never for JAK2; independent assay completion is not adjudicated. Native-missing analyses are reported separately and must not be substituted into the paired complete-case comparison.',
        '', '### Table 1. Tested versus not tested/unknown','',table(concise_baseline(output/'table1_baseline.csv')),
        '', 'Percentages use observed values; missing counts are separate. Continuous age is mean ± SD and median [IQR]. P-values are descriptive and not used for model selection.',
        '', '### Table 2. Positive versus negative global evaluations','',table(concise_baseline(output/'table2_positive_negative.csv')),
        '', '### Testing patterns by sex','',table(sex),
        '', 'Sex differences describe selection and testing yield. No analysis in this package establishes a causal link to recurrence or supports a sex-specific testing recommendation.',
        '', '### Table 3. Recalculated clinical profiles for negative results','',table(pd.read_csv(output/'table3_recalculated_profiles.csv')),
        '',f"FP-Growth retained {assoc['retained_rules']} rules meeting the newly declared thresholds. The historical claim of 4,805 rules is replaced by this reproducible specification. Rule support means P(antecedent AND negative outcome), whereas antecedent support means P(antecedent). These are exploratory descriptions, not validation of rule-based withholding of testing.",
        '', '### Table 5. Paired primary model performance in nested development validation','',table(display_performance(primary)),
        '', 'The operating target was 90% sensitivity in inner training predictions, not a guarantee of 90% sensitivity in independent validation. AUC for the integer score uses its own calibrated probability; the CSV also reports mean within-fold raw-point AUC. Separate fold-specific thresholds are used in nested CV, and one final development threshold is used for temporal validation.',
        '', '### Calibration and temporal validation','',table(temporal[['label','model','n','positive_n','auc','sensitivity','specificity','npv','tp','fp','tn','fn']]),
        '',table(primary[['label','model','brier','mace','ece']]),
        '', 'MACE is the unweighted mean absolute error across occupied fixed-width bins; ECE weights by bin counts. Calibration of the actual integer score and of the full logistic model are distinct. Small temporal event counts and few predicted-negative patients can make NPV particularly unstable; the confusion matrices must accompany it.',
        '', '### Incomplete-data sensitivity analysis','',table(display_performance(native)),
        '', 'This analysis uses all eligible development patients with native missing handling and all nonconstant pretest predictors. Differences from the principal comparison reflect both the population and candidate feature set, and do not isolate an imputation effect.',
        '', '## Interpretation and replacement conclusion','',
        'The previous claims of markedly improved subtype prediction and near-perfect rule-out performance cannot be retained on the basis of the historical runs. The corrected estimates above are the evidence to report. Interpretation must consider selection for testing, complete-case attrition, variation across outcomes and temporal instability. The study remains exploratory; these models do not establish that thrombophilia testing can safely be withheld. Registry-coded APS and JAK2 require particularly cautious interpretation. Further external validation requires laboratory eligibility information and independent centres or countries unavailable in the current extract.',
        '', '## Figures','']
    for f in figures:
        if f.endswith('.png'):sections+= [f'![{Path(f).stem}]({f})','']
    (output/'replacement_manuscript_sections.md').write_text('\n'.join(sections))
    # A single standalone supplement gives every score an unambiguous source/category label.
    supp=['# Recalculated supplementary material','',
          'This supplement belongs exclusively to this reanalysis. All model denominators differ from raw outcome availability when complete cases are required.','',
          '## Table S1. Predictor definitions and quality rules','',table(pd.read_csv(output/'numeric_and_category_quality.csv')),
          '', 'Derived female-under-45 status requires recorded sex and age. Splanchnic thrombosis combines portal, mesenteric and splenic sites; absence requires all three explicitly negative. Quantitative D-dimer, height without a specified clinical category, known APS, thrombophilia results and follow-up variables are excluded. The platelet boundary of 144 follows the supplied supplementary table and is a prespecified analysis convention, not a claim of harmonized local reference ranges.',
          '', '## Table S2. Recorded availability, interpreted negatives and predictive eligibility','',policy_text,'',table(den),
          '', '## Table S3. Predictor missingness in globally tested patients','',table(pd.read_csv(output/'supplement_missingness.csv').query("group=='Globally tested'")),
          '', '## Table S4. Native-missing XGBoost sensitivity analysis','',table(display_performance(native)),
          '', '## Table S5. Temporal validation, primary models','',table(display_performance(temporal)),
          '', '## Table S6. Calibration summaries','',table(metrics[['label','analysis','validation','model','n','brier','mace','ece']]),
          '', '## Final development score cards','',
          'Points are signed. Add points only for the exact category shown; all reference/unselected categories contribute zero. Cards apply only to patients meeting their documented eligibility and complete-case candidate requirements. The probability equation is expit(intercept + slope × total points). These research cards are not clinical deployment tools.']
    for o in OUTCOMES:
        p=output/o.column/'final_models.json'
        if not p.exists():continue
        for meta in json.loads(p.read_text()):
            if meta['kind']!='lasso':continue
            pts=pd.read_csv(output/o.column/f"{meta['analysis']}_lasso_points.csv")
            supp += ['',f"### {o.label}: {meta['analysis']}",'',
                     f"Development N={meta['training_n']:,}; positive N={meta['training_positive_n']:,}; C={meta['parameters']['C']}. Score probability intercept={meta['score_intercept']:.8g}, slope={meta['score_slope']:.8g}; fixed integer cutoff={meta['integer_cutoff']}. Higher totals indicate greater predicted positivity.",'',
                     table(pts) if len(pts) else 'No nonzero score components were selected; the score is constant.']
    (output/'recalculated_supplement.md').write_text('\n'.join(supp))
    # Each reply is evidence-grounded and keeps its original Word comment identity.
    replies={
      0: ('Missing-data reporting',
          'We distinguish missing outcome labels from missing predictors. Routine subtype outcomes are interpreted according to the declared policy, with JAK2 always requiring explicit results. Predictor missingness has now been recalculated before modelling, separating unknown from explicitly not-performed values. The full table is supplement_missingness.csv and each outcome has its own missingness.csv. The primary comparison uses complete cases for the development-defined candidate set after excluding predictors with >40% missingness; LASSO uses no imputation. XGBoost on the same complete cases provides a paired comparison. A separate XGBoost analysis includes incomplete observations using true NaN blocks and native missing handling. Included/excluded comparisons are exported for every outcome. No unknown history is silently coded as absent. See model_cohort_flow.csv for the actual analytical denominators.'),
      1: ('Confirm subtype-specific tested controls',
          policy_text + ' ' + policy_role + ' Explicit prior carrier status/known APS remains excluded. Prediction IDs and their outcome labels are checked against this declared definition. Neither policy admits patients outside documented global testing. The raw, interpreted and analytical denominators are reported separately in supplement_outcome_denominators.csv and table5_primary_performance.csv.'),
      2: ('Confirm Figure 1 numbers',
          f"The complete registry contains {registry['registry_n']:,} patients; {registry['tested_n']:,} have documented testing, with {registry['positive_n']:,} positive and {registry['negative_n']:,} negative global evaluations. The remaining {registry['not_tested_or_unknown_n']:,} are explicitly untested or unknown. These counts reconcile exactly. The new figure separates the {registry['known_thrombophilia_tested_n']:,} known-carrier/known-APS exclusions and the outcome-specific complete-case development and temporal samples. Use figures/cohort_flow.png and model_cohort_flow.csv. The old 8,345/13,770 counts should not be combined with the full-registry tested count."),
      3: ('Perform missingness analyses or remove the sentence',
          'This work has now been performed. The replacement Methods describes the actual 40% development missingness threshold, the primary complete-case definition, the native-missing XGBoost sensitivity analysis, and comparisons of included versus excluded patients. The candidate set is broader than the final nonzero score terms, so we explicitly describe complete cases for retained candidates rather than only for the final score. Remove the unspecified “Table X” reference and cite recalculated Supplementary Table S3.'),
      4: ('Locate previous missingness work',
          'The old Excel validation JSON files were preprocessing audits rather than manuscript missingness tables. They are now superseded for this paper by supplement_missingness.csv, each outcome/missingness.csv, candidate_availability.csv and included_vs_excluded.csv. These files distinguish original missingness, quality failures and modelling exclusion. Their generation is part of the supported reanalysis command.'),
      5: ('Negative or positive association rules?',
          f"Negative is correct for this exploratory section. The new FP-Growth export explicitly requires a negative-result consequent and retains {assoc['retained_rules']} rules under documented thresholds. Positive thrombophilia remains the outcome for the predictive models. Replace the old rule counts and examples with table3_recalculated_profiles.csv and supplement_negative_association_rules.csv; joint rule support and antecedent support are now distinguished."),
      6: ('Positive or negative score orientation?',
          'The new LASSO models predict a positive registered result. Integer points preserve the signs of their coefficients, so higher total scores indicate greater predicted positivity and a positive decision is score ≥ its development cutoff. The score-to-probability mapping has a nonnegative slope. This orientation is now consistent for both the automatic and composite guided comparison. It supersedes the historical guided card that used the opposite inequality. Each final card reports exact variable/category identities, signed points and its locked threshold.'),
      7: ('Correct and complete Table 1',
          'Table 1 has been rebuilt from mutually exclusive tested versus not-tested/unknown groups in the original registry. It reports observed denominators, missing counts, standardized differences and newly calculated descriptive p-values; no old p-values were carried forward. Table 2 is also rebuilt from the same source. Use table1_baseline.csv and table2_positive_negative.csv, or the formatted replacement manuscript tables. Percentages now use observed values rather than equating unknown history with absence.'),
      8: ('Shorten the sex comparison',
          'We suggest retaining one descriptive sentence in the main Results and moving the full effect sizes and Bayesian conditional probabilities to the supplement. The analysis addresses testing selection and yield but does not establish clinical testing criteria. sex_testing_yield.csv and sex_effect_sizes.csv contain the recalculated counts, rates and intervals from the same original registry.'),
      9: ('Sex, hormone/pregnancy testing and recurrence',
          'The recalculated sex difference can be retained as a descriptive finding. No recurrence model or adjudicated testing-indication analysis has been conducted, so we cannot attribute it to recurrent VTE, contraceptive use or pregnancy. Those are hypotheses, not explanations demonstrated by these results. An additional important correction is that trat_est means statin treatment; hormone exposure is fr_estro. The prior score label “estrogen treatment” for trat_est was erroneous.'),
      10: ('Complete Table 5 and report both XGBoost and integer scores',
          'Both models are retained because their comparison is a study objective. They now use exactly the same complete-case patients in the primary table; the full logistic LASSO benchmark is also supplied. N, positives, AUC, TP/FP/TN/FN, all threshold metrics, calibration and resource calculations come from the same stored predictions. The native-missing tree results are a separate sensitivity table. Antithrombin and JAK2 have been recomputed; JAK2 remains descriptive because of its small event count. The observed sensitivity is allowed to fall below 90% in validation: the 90% target selects training thresholds and must not be enforced retrospectively on held-out patients.'),
      11: ('Identify the calibration figures and numbers',
          'The authoritative files are supplement_calibration.csv, all_model_metrics.csv and figures/<outcome>_validation.png. Calibration now evaluates the actual point-score probability separately from the full logistic prediction. Recalculated Supplementary Table S6 reports Brier, MACE and ECE with explicit bin definitions. The old MACE values and placeholder Figure X should be removed. No number in the legacy calibration summary is reused.'),
      12: ('Identify and verify temporal validation',
          f"Temporal validation is now a fixed {config['cutoff_year']}/{config['cutoff_year']+1} split. All category vocabularies, supervised screening, hyperparameters, score cards, probability mappings and thresholds are fitted in development only. supplement_temporal_validation.csv identifies each outcome, model, N, events and confusion matrix; the formatted primary table is Supplementary Table S5. Undefined NPV is reported as undefined, not zero. Small holdout/event counts are displayed and must accompany interpretation. The previous temporal figures have been replaced rather than relabelled."),
    }
    reply_sections=['# Responses to all Word comments — recalculated analysis','',
        'All replies below refer to the completed reanalysis directory containing this document. Original comment IDs are preserved (zero-based). The source Word files were not edited in place.','',
        '## Applied outcome interpretation','',policy_text,'','## Current analysis populations','',table(flows,['label','eligible_n','development_complete_n','temporal_complete_n','missing_excluded_n']),
        '', '## Current primary performance','',table(display_performance(primary))]
    for id,(title,text) in replies.items():
        reply_sections += ['',f'## Article comment {id}: {title}','',text]
    subtype=den[den.outcome!='ana_dura'].copy()
    effective='interpreted_tested_n' if 'interpreted_tested_n' in subtype else 'tested_binary_n'
    subtype['positive_percent']=100*subtype.tested_positive_n/subtype[effective]
    subtype_columns=['label','tested_binary_n','tested_positive_n',effective,'positive_percent','tested_unavailable_n','known_excluded_n','eligible_n']
    subtype_columns=list(dict.fromkeys(subtype_columns))
    if 'missing_interpreted_negative_n' in subtype:subtype_columns.insert(3,'missing_interpreted_negative_n')
    reply_sections += ['', '## Supplement comment 0: Missing values in subtype distribution','',
        policy_text + ' Supplementary Table S2 separates raw explicit binary results, recorded positives, missing-to-negative interpretations, remaining unavailable results and known-carrier exclusions. Positivity uses the interpreted tested denominator for the chosen policy, not the proportion of diagnoses among globally positive patients. The table below gives availability and interpretation before predictive exclusions:',
        '',table(subtype,subtype_columns),
        '', '## Where to find the manuscript-ready text','',
        'replacement_manuscript_sections.md/.docx contains the replacement Methods, Results, conclusion and main tables. recalculated_supplement.md/.docx contains definitions, missingness, temporal/calibration tables and all final score cards. CSV files are the numeric source of truth; figures/ contains standalone PNG and SVG files.',
        '', '## Remaining limitations that wording cannot remove','',
        'No independent assay-completion flag, laboratory repeat-confirmation record, anticoagulant-at-assay timestamp, or centre/country validation identifier was available. Those limitations are reported explicitly. The routine-panel interpretation comes from the study investigators, not from independent confirmation in this extract. Complete-case attrition and the exploratory nature of the cards remain substantive limitations.']
    (output/'coauthor_responses.md').write_text('\n'.join(reply_sections)+'\n')
    (output/'README.md').write_text('''# Authoritative manuscript reanalysis outputs

Start with `coauthor_responses.md` (all 14 Word comments),
`replacement_manuscript_sections.md` (replacement text and main tables), and
`recalculated_supplement.md` (supplement and final cards). DOCX copies are generated
when Pandoc is installed. Narrative documentation and replies are in English.

`run_manifest.json` records parameters, hashes, software versions, completion
status and outcome selection. Only a complete manifest is a finished numerical
run. `table5_primary_performance.csv` uses paired complete cases and nested CV;
`supplement_native_missing_performance.csv` is a separate sensitivity analysis.
`model_cohort_flow.csv` explains every modelling denominator. The sex and raw
subtype availability tables intentionally precede predictive known-carrier
exclusions; their denominators must not be used for model metrics.

Each local research outcome directory contains held-out `predictions.parquet`, `metrics.csv`,
`calibration.csv`, candidate/missingness/exclusion audits, the nested search log,
final development cards, locked models and automated numerical quality checks.
Patient prediction files contain registry identifiers and stay local, outside
Git. Fitted model binaries also stay local. Word/PDF documents are optional
local exports; Markdown, aggregate CSV/JSON and figures are versioned. Public
manifest verification uses `outputs_sha256`; `local_artifacts` and
`optional_exports` are separate inventories and are not required in a clone. Final model files are development-only fits;
do not substitute their in-sample predictions for validation estimates.

The source Word documents remain local, and historical aggregate results were preserved. Legacy files
are under `out/archive/`; the 7 September explicit-results run is an alternative
policy analysis, not the current routine-panel principal result.
Run instructions and technical contracts are in
`docs/docs_source/manuscript_reanalysis.rst`.
''')
    with (output/'README.md').open('a') as handle:
        handle.write('\n' + policy_role + '\n')
        if (output/'outcome_policy_comparison.md').exists():
            handle.write('\nSee `outcome_policy_comparison.md` for the aggregate comparison with the earlier explicit-results run.\n')
    if config['compact']:
        for name in ['coauthor_responses','replacement_manuscript_sections','recalculated_supplement']:
            p=output/(name+'.md')
            p.write_text('**TEST-ONLY COMPACT RUN — NOT FOR MANUSCRIPT REPORTING.**\n\n'+p.read_text())
    reference=create_word_reference(output)
    for stem in ['coauthor_responses','replacement_manuscript_sections','recalculated_supplement']:
        # Run in the report directory so embedded image references resolve in DOCX.
        if shutil.which('pandoc'):
            subprocess.run(['pandoc',stem+'.md','--reference-doc='+reference.name,'-o',stem+'.docx'],cwd=output,check=True)
    metadata=dict(generated_reports=['coauthor_responses','replacement_manuscript_sections','recalculated_supplement'],
                  comment_count=14,figure_files=figures,report_code_sha256=__import__('hashlib').sha256(Path(__file__).read_bytes()).hexdigest())
    (output/'report_manifest.json').write_text(json.dumps(metadata,indent=2)+'\n')
    if manifest.get('status') == 'complete':
        from manuscript_reanalysis import hash_file, write_json
        manifest.update(artifact_inventory(output))
        write_json(output/'run_manifest.json',manifest)


def create_word_reference(output: Path) -> Path | None:
    """Create a landscape A4 reference so wide scientific tables stay reviewable."""
    if not shutil.which('pandoc'):
        return None
    path=output/'report_reference.docx'
    payload=subprocess.check_output(['pandoc','--print-default-data-file=reference.docx'])
    from io import BytesIO
    ns='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
    w=lambda name:'{'+ns+'}'+name
    with ZipFile(BytesIO(payload)) as source:
        files={name:source.read(name) for name in source.namelist()}
    root=ET.fromstring(files['word/document.xml'])
    for section in root.iter(w('sectPr')):
        size=section.find(w('pgSz'))
        if size is None:size=ET.SubElement(section,w('pgSz'))
        size.set(w('w'),'16838');size.set(w('h'),'11906');size.set(w('orient'),'landscape')
        margins=section.find(w('pgMar'))
        if margins is not None:
            for side in ['top','bottom','left','right']:margins.set(w(side),'720')
    files['word/document.xml']=ET.tostring(root,encoding='utf-8',xml_declaration=True)
    root=ET.fromstring(files['word/styles.xml'])
    defaults=root.find('.//'+w('docDefaults')+'/'+w('rPrDefault')+'/'+w('rPr'))
    if defaults is not None:
        for name in ['sz','szCs']:
            size=defaults.find(w(name))
            if size is None:size=ET.SubElement(defaults,w(name))
            size.set(w('val'),'20')
    files['word/styles.xml']=ET.tostring(root,encoding='utf-8',xml_declaration=True)
    from zipfile import ZIP_DEFLATED
    with ZipFile(path,'w',ZIP_DEFLATED) as target:
        for name,data in files.items():target.writestr(name,data)
    return path


def main() -> None:
    """Regenerate narrative/figure outputs from an already completed numerical run."""
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('output_dir',type=Path)
    args=parser.parse_args();generate_reports(args.output_dir)

if __name__=='__main__':main()
