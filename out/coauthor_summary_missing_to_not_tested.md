# Coauthor Summary: Reclassifying Missing `ana_dura` as `No buscada`

After review, we harmonized the preprocessing rule for `ana_dura` so that missing values are no longer treated as a separate implicit category. Instead, all missing `ana_dura` entries are now recoded to `No buscada` before any downstream analyses are run. This change was applied consistently across the analytical pipeline, manuscript-support outputs, and documentation.

## What changed

Previously, the descriptive comparison of tested versus not-tested patients used a narrow definition of `not tested` that included only records explicitly labeled `No buscada`. Under that earlier definition, the not-tested cohort contained 35,784 patients, while 60,791 additional records had missing `ana_dura` and were effectively left outside that comparison.

After the update, `not tested` is defined as all patients classified as `No buscada` after preprocessing normalization, which now includes both:

- patients explicitly labeled `No buscada`, and
- patients whose `ana_dura` value was originally missing.

As a result, the cohort counts are now:

- Tested (`Buscada positivo` or `Buscada negativo`): **22,874**
- Not tested (`No buscada` after normalization): **96,575**
- Total registry rows: **119,449**

## Why this is methodologically preferable

This update makes the cohort definition internally consistent. If a thrombophilia study label is missing, that record should not be interpreted as belonging to an unknown third comparison group when the analytical question is whether the patient was tested versus not tested. Reclassifying missing `ana_dura` values as `No buscada` therefore avoids an artificial loss of denominator information and yields a cleaner binary comparison.

## Practical effect on the results

The main effect is on the descriptive tested-versus-not-tested comparison and on any downstream screening outputs that target the not-tested population.

In the revised baseline table:

- the tested cohort remains unchanged at **22,874**;
- the not-tested cohort increases from **35,784** to **96,575**;
- descriptive characteristics of the not-tested group shift accordingly, because it now reflects the full set of patients without a confirmed thrombophilia study label.

The updated baseline comparison now shows, for example:

- Age, mean (SD): **55.2 (18.1)** in tested vs **67.7 (16.1)** in not tested
- Female sex: **47.1%** in tested vs **50.7%** in not tested
- Active cancer: **11.7%** in tested vs **27.8%** in not tested
- Immobilization: **19.1%** in tested vs **23.7%** in not tested

These revised numbers should be used wherever the manuscript contrasts tested and not-tested patients.

## Impact on interpretation

This change does **not** alter the definition of the tested subgroup used for the outcome-specific score analyses. The tested cohort remains the set of patients with `Buscada positivo` or `Buscada negativo`, and the outcome-prevalence summaries among tested patients are unchanged.

What does change is the interpretation of the comparator population. The manuscript should now describe the not-tested group as the set of patients classified as `No buscada` after preprocessing normalization of missing study labels, rather than as only the subset explicitly coded `No buscada` in the raw registry.

## Recommended wording for the manuscript

A concise wording option is:

> Missing `ana_dura` values were normalized to `No buscada` during preprocessing; therefore, the not-tested cohort included both patients explicitly coded as not searched and patients without a recorded thrombophilia-study label.

If needed, the Results section can also state:

> Among 119,449 registry rows, 22,874 patients were classified as tested (`Buscada positivo` or `Buscada negativo`), whereas 96,575 were classified as not tested (`No buscada`) after normalization of missing thrombophilia-study labels.
