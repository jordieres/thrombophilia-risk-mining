# Revisión del artículo y del suplemento — 7 de septiembre de 2026

La revisión identifica desalineamientos sustanciales que afectan a la población analizada, la metodología y la interpretación del rendimiento. No basta con corregir la redacción o cambiar los denominadores de las tablas: los modelos por subtipo necesitan una nueva ejecución sobre una cohorte y unos predictores definidos de forma coherente.

Se han revisado los dos Word, sus dos figuras incrustadas, los 14 comentarios conservados en `word/comments.xml` (13 del artículo y 1 del suplemento), el código y los resultados locales. Se han recalculado recuentos y ausencias desde los parquet y comprobado la pertenencia de las predicciones históricas a las cohortes mediante el identificador del paciente. Las instrucciones internas de los documentos se han tratado como material de revisión. No se han modificado los originales ni reentrenado modelos. Los números propuestos como descriptivos no son resultados de modelos nuevos.

## 1. Hallazgos prioritarios

### 1.1. Se mezclan el registro original, la base depurada y distintas ejecuciones

| Población | Registro original | Base depurada patD_slim |
|---|---:|---:|
| Total | 119.449 | 114.757 |
| Estudio positivo o negativo registrado | 22.874 | 22.115 |
| Resultado positivo global | 8.568 | 8.345 |
| Resultado negativo global | 14.306 | 13.770 |
| No estudiado o etiqueta ausente | 96.575 | 92.642 |

La reducción de 119.449 a 114.757 corresponde a 4.692 filas eliminadas por criterios de depuración numérica, según `data/patD_spec_subset_validation.json`, no a una actualización del registro. Entre los estudiados se pierden 759 filas. Por tanto, 8.345 positivos y 13.770 negativos no pueden presentarse como la partición completa de 22.874 pacientes.

El resumen y Métodos usan la base original; la Tabla 2 y parte de Resultados usan la depurada. La Figura 1 combina ambas dentro de la propia imagen, mientras su leyenda mantiene 114.757/22.115. La imagen llama “Excluded” a una recodificación que conserva las filas; debe decir “Reclassified”. También indica 174 variables, frente a 168 columnas en el parquet original y 83 en patD_slim: hay que documentar a qué conjunto se refiere. Los porcentajes por sexo del bloque “Not tested” no representan la composición de ese grupo, pese a lo que dice la leyenda.

### 1.2. Los controles por subtipo no cumplen la restricción declarada

El filtro de `src/exp_clinical_risk_score.py::_filter_binary_target` conserva Sí/No del subtipo, pero no exige `ana_dura` positivo o negativo. Lo mismo ocurre en `src/manuscript_support.py::generate_review_package`. Hay 20.761 pacientes con etiqueta global no estudiada/ausente y un “No” en cada uno de seis subtipos. No puede asumirse que ese “No” demuestre una prueba específica realizada; hay una incoherencia de codificación que requiere aclaración del diccionario/registro.

| Subtipo | Sí/No en registro completo | Sí/No dentro de los 22.874 estudiados | Positivos dentro de estudiados | Positividad | Sin Sí/No dentro de estudiados |
|---|---:|---:|---:|---:|---:|
| Proteína C | 31.036 | 10.275 | 356 | 3,46% | 12.599 |
| Proteína S | 31.076 | 10.315 | 757 | 7,34% | 12.559 |
| Factor V Leiden | 31.399 | 10.638 | 2.048 | 19,25% | 12.236 |
| Protrombina | 31.137 | 10.376 | 1.602 | 15,44% | 12.498 |
| Antitrombina | 31.094 | 10.333 | 260 | 2,52% | 12.541 |
| APS registrado | 31.471 | 10.710 | 1.908 | 17,82% | 12.164 |
| JAK2 | 2.246 | 2.246 | 61 | 2,72% | 20.628 |

Estos son denominadores de resultados binarios registrados dentro del grupo globalmente estudiado, no una certificación independiente de realización de cada ensayo. “Sin Sí/No” tampoco distingue no realizado de no documentado.

La comprobación de los CSV históricos confirma que el problema llegó a resultados publicados: las predicciones de FVL contienen 30.700 pacientes, de los que 20.385 están fuera del grupo globalmente estudiado. Los HTML históricos reproducen las AUC del artículo para FVL (0,800/0,843), protrombina (0,799/0,829), proteína S (0,733/0,800) y proteína C (0,710/0,768), para score/XGBoost. Por tanto, la coincidencia de cifras no valida su atribución a las nuevas cohortes de aproximadamente 10.000 pacientes.

### 1.3. La Tabla 5 combina rendimiento histórico con denominadores nuevos

Ejemplo verificable: FVL integer proviene de TP=1.865, FP=17.045, TN=11.675, FN=115; N=30.700 y positivos=1.980. Esos recuentos producen sensibilidad 94,2%, especificidad 40,7%, PPV 9,9% y NPV 99,0%. El artículo conserva esas métricas, pero cambia N a 10.638 y positivos a 2.048. La fila ya no es coherente.

Con N=10.638, positivos=2.048 y las sensibilidades/especificidades redondeadas del artículo, las identidades aritméticas exigirían aproximadamente PPV=27,5% y NPV=96,7%. Esto es una comprobación de incompatibilidad, NO una estimación corregida del rendimiento: al cambiar la cohorte hay que volver a entrenar y validar.

Las pruebas evitadas y positivos omitidos deben calcularse de la misma matriz: 1.000×(TN+FN)/N y 1.000×FN/N. El CSV `table5_arithmetic_check_NOT_model_results.csv` comprueba las filas con denominador disponible. En el compuesto integer, 93,2%/9,4% y 8.345/22.874 implican aproximadamente 84,5 pruebas evitadas y 24,8 positivos omitidos por 1.000, no 94 y 36. La fila APS integer también es incompatible. No rellenar los huecos con números de otras ejecuciones.

### 1.4. La metodología descrita no corresponde al score implementado

- **Regresión:** `LogisticRegression(solver='liblinear', class_weight='balanced')`, sin especificar L1, corresponde a L2 en el entorno utilizado. No se encuentra selección univariable p<0,10, LASSO ni búsqueda de la penalización por CV en esta ruta. La selección final usa signo del coeficiente, prevalencia mínima y un máximo de componentes.
- **XGBoost:** la ruta del score fija profundidad 3, learning rate 0,08, subsample/colsample 0,8 y número configurable de árboles. No ejecuta el ajuste de hiperparámetros descrito en P58.
- **Ausencias:** categorías “Missing”, imputación constante y one-hot encoding para ambos modelos; no es análisis de casos completos ni una estrategia exclusivamente nativa de missing de XGBoost. Algunas ausencias de antecedentes se convierten en “No” de forma directa, sin consulta cruzada a otras partes de la historia clínica.
- **Cortes:** el score automático usa cuantiles (`pd.qcut`), no exclusivamente las categorías clínicas de la Tabla S1. Los cuantiles se calculan antes de separar folds y antes de la partición temporal; hay acceso a la distribución de validación que debe evitarse en una nueva ejecución.
- **Umbral:** se elige sobre predicciones agrupadas fuera de fold para alcanzar sensibilidad mínima. Está predefinido el objetivo de sensibilidad, no necesariamente el valor numérico del umbral. La evaluación de ese punto operativo no es una validación independiente de su selección.
- **Score final:** los puntos se vuelven a estimar con todos los datos para exportar la tarjeta. Las métricas CV proceden de tarjetas entrenadas por fold, no de una evaluación externa de esa tarjeta final.

### 1.5. La auditoría anterior admite predictores incompatibles con el uso pretest

La preparación reproducida para FVL sobre el registro original admite `ana_dura`, `ana_port`, otros resultados de trombofilia (`var154`, `var155`, `var157`, `var158`, `var161`, `anadutip`) y variables `evn_*`. La presencia de resultados relacionados con el desenlace contradice la exclusión de información posterior o dependiente del test. Las variables de seguimiento requieren además revisar su disponibilidad temporal.

Los subconjuntos depurados contienen también variables `evn_*`, por lo que la simple selección del Excel no acredita que todo predictor sea pretest. La frase que afirma exclusión de portadores previos tampoco queda acreditada: `ana_port` no contiene positivos explícitos en el parquet inspeccionado; no se identifica una exclusión individual trazable por ese criterio.

`out/coauthor_response_review.md` **no debe reutilizarse como respuesta final**: afirma analizar solo estudiados, etiqueta como “tested” las cohortes de más de 31.000 y resume modelos preparados con la selección amplia anterior. Sus resultados no corrigen los modelos históricos.

### 1.6. Calibración y validación temporal no corresponden limpiamente al modelo publicado

Los MACE de P468 no coinciden con `out/calibration_model_summary.csv`: este contiene aproximadamente 0,091 APS, 0,062 FVL, 0,072 protrombina, 0,094 proteína S y 0,092 proteína C para “Automatic Integer Score”. Además, el código calibra `predict_proba` de la logística completa, no una probabilidad derivada de la suma simplificada de puntos; por eso coincide con el benchmark logístico. No procede sustituir mecánicamente unos números por otros.

Los valores temporales de P469 sí aparecen en `out/temporal_validation_summary.csv`, pero pertenecen a cohortes amplias y a esa ruta de predictores. La tabla no identifica los subtipos: el orden del código es C, S, FVL, protrombina y APS. Las validaciones contienen 222, 231, 240, 223 y 269 pacientes, respectivamente. En APS: TP=121, FP=146, TN=0 y FN=2; NPV=0 se basa en solo dos predicciones negativas. Debe explicitarse ese denominador.

El corte 2021 se selecciona buscando el último año que cumple condiciones de tamaño y presencia de ambas clases; no está fijado literalmente de antemano. El suplemento adjunto no contiene la figura de calibración X ni la tabla temporal Y anunciadas.

### 1.7. Otros desajustes de texto, tablas y figuras

- Tabla 1: edades medianas, sexos y factores clínicos mezclan columnas/poblaciones. Hay 41.915 hipertensos bajo una columna de solo 22.874 personas: error inequívoco. Su pie sigue describiendo registro completo frente a estudiados, aunque la cabecera dice estudiados frente a no estudiados.
- Tabla S2: mezcla positividad dentro del subtipo (FVL 19,3%) con distribución dentro de los 8.345 positivos globales (APS 22,9%, etc.). Protrombina 1.559, S 730 y C 338 pertenecen a la base depurada; los nuevos denominadores son de la original.
- Figura suplementaria 1: la imagen muestra score **azul** y logística **roja**, con AUC logística **0,590**; el pie invierte los colores y escribe **0,588**. Score 0,553 y umbral 3 sí coinciden visualmente.
- Reglas: el código de contraste puede generar reglas para varios desenlaces; no acredita por sí solo una búsqueda exclusivamente negativa. No se ha localizado una ejecución persistida que reproduzca conjuntamente 4.805 reglas y el ejemplo 89,2%/1,4%. El checkpoint disponible es de 300 filas y otros parámetros. El soporte de una regla en el código es P(antecedente y consecuente), no P(antecedente), como afirma P49; ello afecta a la interpretación de n≈320.
- Tarjetas: “Estrogen treatment” y “Estrogen use” requieren mantener el código de origen (`trat_est`/`fr_estro`) y revisar sus etiquetas para evitar duplicación aparente. Las categorías one-hot pueden representar la ausencia de una condición (`_No`), por lo que no basta con traducir el nombre de la variable como presencia. No se certifica aquí cada punto sin la tabla de coeficientes de la ejecución correspondiente.
- APS: la ausencia de confirmación repetida en el extracto no demuestra que cada paciente recibiera una única determinación. Es más defendible “registry-coded APS; repeat-test confirmation was unavailable in this extract” que afirmar que el registro lo define universalmente por una sola prueba positiva.

## 2. Respuestas a los 14 comentarios

Los identificadores siguientes son los IDs internos del Word, empezando por cero. Se incluye la localización textual porque la paginación depende de Word. Los párrafos P remiten a las extracciones adjuntas.

### Artículo, comentario 0 — Pablo — missing data (P20)

**Respuesta para trasladar:** De acuerdo. He calculado una tabla de ausencias por variable antes de su tratamiento, con denominadores explícitos, disponible en `missingness_by_variable.csv`. En los 22.874 estudiados del registro original: edad 0%; raza 58,73%; hipertensión 23,12%; antecedentes familiares 69,27%; hemoglobina y leucocitos 0,17%; plaquetas 0,16%; PCR (`protcrea`) 97,14%. En D-dímero categórico hay 1.603 ausentes (7,01%) y 5.064 “No practicado” (22,14%), que deben mostrarse separados. El D-dímero cuantitativo tiene 86,93% de ausencia.

La ruta XGBoost del score utiliza las mismas categorías/imputación constante y codificación one-hot que la logística; no podemos describirla simplemente como manejo nativo de missing. La logística tampoco usa casos completos ni LASSO en esta implementación. No se ha identificado una comparación previa específica de excluidos por missing; las 4.692 exclusiones documentadas son por criterios numéricos de depuración, no deben rebautizarse como exclusiones por ausencia. Los porcentajes deben recalcularse para la cohorte definitiva si se elige la base depurada u otra población.

**Matiz:** el CSV distingue nulos, sentinelas y etiquetas explícitas; cero missing después de imputar no equivale a datos originalmente completos. La tabla basal reconstruida incluye valores numéricos extremos del original y no debe publicarse sin su control de calidad.

### Artículo, comentario 1 — Lucía — “Confirmar que esto es así” (P26)

**Respuesta para trasladar:** No se puede confirmar en la versión actual. El filtro usado en los modelos por subtipo selecciona Sí/No sin exigir que el estudio global conste realizado. Hemos comprobado controles fuera de la cohorte estudiada en las predicciones históricas. Los N=10.275–10.710 describen la intersección entre resultado binario y estudio global registrado, pero las métricas de las tablas provienen de cohortes mayores. Hay que aclarar el significado del “No” específico, aplicar una definición verificable de elegibilidad y repetir los modelos; después podrá mantenerse esta frase.

### Artículo, comentario 2 — Lucía — “Confirmar números” (P27 / Figura 1)

**Respuesta para trasladar:** Para el registro original son 119.449 en total, 22.874 estudiados, 96.575 no estudiados/etiqueta ausente, 8.568 positivos y 14.306 negativos. Los 8.345/13.770 de la figura son de la base depurada y suman 22.115. En la figura actual faltan por ello 759 personas respecto a su rama de 22.874. Hay que optar por una población y mostrar, si procede, el paso de depuración. En la original los positivos son 37,46% y los negativos 62,54% de los estudiados. Corregir también el pie, “Excluded”, porcentajes por sexo y el número de variables.

### Artículo, comentario 3 — Pablo — “deberíamos hacer esto; si no se puede se quita” (P40)

**Respuesta para trasladar:** La descripción actual no corresponde al procedimiento ejecutado. Ya está disponible el inventario de ausencias, pero no hemos realizado ahora una nueva estrategia de exclusión por missing ni un análisis de casos completos. Propongo sustituir ese párrafo por la descripción real del preprocesamiento, e incorporar una tabla de ausencias de la cohorte definitiva. No debe decirse que se excluyeron variables por “excessive missingness” sin documentar un umbral y las variables afectadas.

### Artículo, comentario 4 — Lucía — “Me suena que lo hicimos pero no lo encuentro” (P40)

**Respuesta para trasladar:** Sí existen auditorías parciales: `data/patD_spec_subset_validation.json` y `out/archive/patD_var*_validation.json` documentan transformaciones, rellenos y exclusiones por criterios del Excel. No equivalen a la Tabla X prometida ni acreditan casos completos. He añadido un inventario reproducible de ausencias originales y categorías no realizadas. La frase debe referirse a esta tabla solo después de elegir el denominador analítico final.

### Artículo, comentario 5 — Lucía — “negative o positive?” (P45)

**Respuesta para trasladar:** Para esta sección puede ser **negative**, si se presentan las reglas cuyo consecuente es resultado negativo. Eso es compatible con que el modelo predictivo posterior tenga como desenlace positivo la trombofilia. El código general genera reglas para distintos resultados; propongo titular “Exploratory association rules for negative thrombophilia results” y recuperar la ejecución que sustenta las reglas concretas antes de confirmar sus recuentos y porcentajes.

### Artículo, comentario 6 — Lucía — “¿positivo o negativo?” (P63)

**Respuesta para trasladar:** En el **score automático** se modela el positivo y los puntos proceden de coeficientes positivos: más puntos indican mayor propensión al positivo; la decisión positiva es score ≥ umbral. En el **score guiado por asociaciones** se seleccionan coeficientes negativos: más puntos indican menor propensión al positivo y la decisión positiva se aplica con score ≤ umbral. No hay contradicción si se distinguen ambas estrategias. Dado que se reporta el automático, esta frase puede mantenerse referida expresamente a él, corrigiendo la descripción de LASSO y de selección de variables.

### Artículo, comentario 7 — Lucía — Tabla 1 incompleta/incorrecta (P84–135)

**Respuesta para trasladar:** Confirmado: la tabla mezcla poblaciones y posiciones de columnas. Para registro original, estudiados frente a no estudiados/etiqueta ausente: edad media 55,2±18,1 frente a 67,7±16,1; mediana [IQR] 56 [41–70] frente a 71 [58–80]; mujeres 10.781 (47,1%) frente a 48.943 (50,7%); hipertensión 6.232 (27,2%) frente a 37.751 (39,1%); diabetes 1.950 (8,5%) frente a 13.034 (13,5%); tabaquismo activo 3.493 (15,3%) frente a 9.271 (9,6%); cáncer 2.671 (11,7%) frente a 26.850 (27,8%); inmovilización 4.361 (19,1%) frente a 22.903 (23,7%); VTE previo 3.062 (13,4%) frente a 12.896 (13,4%); historia familiar 909 (4,0%) frente a 1.839 (1,9%).

Estos porcentajes usan el grupo completo como denominador y presencia explícita, con el tratamiento de antecedentes del pipeline; hay que acompañarlos de missing y evitar interpretar ausencia de registro como ausencia clínica demostrada. He guardado `baseline_recomputed.csv`. Rehacer p-valores si se mantienen; no reutilizar los antiguos. Es preferible añadir diferencias estandarizadas. Corregir también Tabla 2 si se decide usar la base original.

### Artículo, comentario 8 — Pablo — reducir comparación por sexo (P198)

**Respuesta para trasladar:** Propongo conservar una frase descriptiva en Resultados y trasladar el detalle de RR/OR/intervalos al suplemento. La comparación responde al objetivo de describir la selección para testing, pero no necesita dominar el resumen ni la discusión. Hay que recalcularla en la misma población: 39,5% frente a 35,8% corresponde a la base depurada; en el registro original el rendimiento positivo es 39,25% en hombres y 35,45% en mujeres.

### Artículo, comentario 9 — Lucía — interés del sexo y posible relación con recurrencia (P198)

**Respuesta para trasladar:** Podemos mantenerlo como hallazgo descriptivo sobre selección y rendimiento del testing. En el registro original se estudió al 20,25% de los hombres y al 18,05% de las mujeres. Este análisis no evalúa si la diferencia de rendimiento explica recurrencias, ni controla específicamente indicaciones por anticonceptivos o embarazo. La relación con recurrencia puede formularse como hipótesis para otro análisis, pero no como explicación demostrada por estos resultados. El registro local no aporta en este análisis una indicación de testing adjudicada que permita resolverlo.

### Artículo, comentario 10 — Lucía — Tabla 5: faltan datos; XGBoost e integer (P270–429)

**Respuesta para trasladar:** Mantendría ambos, porque la comparación entre rendimiento y simplificación es un objetivo central. En la tabla principal pueden quedar AUC, sensibilidad, especificidad y utilidad de XGBoost/score automático; matrices completas, intervalos y detalles de umbral pueden ir al suplemento. Antes hay que rehacer la tabla: N y positivos se han actualizado sin recalcular métricas, lo que genera incompatibilidades matemáticas. Antitrombina tiene 10.333 resultados binarios y 260 positivos dentro de la cohorte original estudiada; JAK2 tiene 2.246 y 61. Son recuentos descriptivos confirmados, no los N de entrenamiento demostrados para sus AUC. No rellenaría todavía sus celdas de rendimiento.

Para cada ejecución deben salir conjuntamente N, positivos, AUC, umbral, TP/FP/TN/FN, PPV/NPV, evitados y omitidos por 1.000. No completar los huecos de XGBoost con cálculos basados en prevalencias de otra cohorte. Las métricas de APS y del compuesto requieren recuperar su procedencia exacta; el archivo actual de salida del compuesto es otra ejecución (N=4.000, AUC automática 0,985).

### Artículo, comentario 11 — Lucía — “No sé cuáles son ya” (P468, calibración)

**Respuesta para trasladar:** Los archivos disponibles son `out/calibration_summary.csv`, `out/calibration_model_summary.csv` y `out/calibration_overview.html`. Sin embargo, sus MACE no coinciden con los del párrafo y no corresponden de forma válida a la tarjeta simplificada publicada: el cálculo usa probabilidades de la logística completa, además de una cohorte/predictores distintos. El suplemento adjunto no contiene la Figura X. Propongo retirar provisionalmente las cifras de ese párrafo y generar calibración del modelo correcto en la nueva ejecución, con una función explícita que transforme puntos en probabilidad si se quiere calibrar el score.

### Artículo, comentario 12 — Lucía — “Same” (P469, temporal)

**Respuesta para trasladar:** La fuente es `out/temporal_validation_summary.csv`. Los números citados se encuentran allí; las filas son C, S, FVL, protrombina y APS, aunque falta una columna identificadora. No validan las tarjetas del artículo sobre sus nuevos denominadores: se calcularon sobre cohortes amplias, con selección de variables incompatible con la restricción pretest y discretización anterior a la partición. La Tabla Y tampoco está incluida en el Word. Hay que repetir la validación con predictores, cortes y umbral fijados en desarrollo, identificar cada desenlace e informar N y eventos. Para APS, el NPV de 0% procede de dos predicciones negativas, ambas falsos negativos; no presentarlo sin ese contexto.

### Suplemento, comentario 0 — Lucía — “Missing values” (Tabla S2, P59–89)

**Respuesta para trasladar:** Si se desea informar positividad por prueba dentro de los 22.874 estudiados, los datos son: FVL 2.048/10.638 (19,25%); APS 1.908/10.710 (17,82%); protrombina 1.602/10.376 (15,44%); proteína S 757/10.315 (7,34%); proteína C 356/10.275 (3,46%); antitrombina 260/10.333 (2,52%); JAK2 61/2.246 (2,72%). Añadir una columna de resultado específico no disponible: 12.236, 12.164, 12.498, 12.559, 12.599, 12.541 y 20.628, respectivamente. Esas ausencias incluyen posibles pruebas no realizadas y resultados no documentados, que no podemos separar solo con Sí/No.

Cambiar el pie para definir el denominador específico por prueba. Si se quiere mantener la distribución de diagnósticos entre positivos globales, debe ser otra tabla/columna con su denominador explícito; no mezclar ambos porcentajes. Los subtítulos no son mutuamente excluyentes y no se espera que sumen el total de pacientes.

## 3. Redacción metodológica utilizable para describir el código auditado

Este texto describe la ruta de score revisada; no pretende legitimar los resultados antiguos ni sustituir la necesaria nueva ejecución:

“Candidate predictors were encoded as categorical features, with continuous variables discretized using data-derived quantile intervals. Missing categorical values were represented by an explicit missing category and features were one-hot encoded. Integer scores were derived from class-balanced L2-regularized logistic regression. Eligible positive coefficients were selected according to prevalence and component-count criteria, scaled by the smallest retained positive coefficient and rounded to integer points. XGBoost benchmarks used the same feature representation and fixed hyperparameter settings. Discrimination was evaluated using stratified cross-validation; operating thresholds were selected from pooled out-of-fold predictions to achieve the target minimum sensitivity.”

Antes de incorporarlo, completar número de folds, componentes, bins y parámetros con el manifiesto de la ejecución finalmente reportada. Para una metodología corregida, la selección de predictores, discretización, calibración y umbral deben aprenderse exclusivamente en desarrollo.

## 4. Trabajo necesario antes de cerrar el manuscrito

1. Fijar población: registro original para descripción y, si procede, cohorte depurada para modelos con diagrama de exclusiones completo. Resolver la discordancia entre `ana_dura` y “No” específico con el diccionario del registro.
2. Definir una lista explícita de predictores pretest, excluyendo resultados de trombofilia y variables posteriores; documentar portadores conocidos, temporalidad y ausencias.
3. Ejecutar nuevamente compuesto y subtipos sobre sus poblaciones verificadas; entrenar preprocesamiento dentro de cada partición; fijar y registrar hiperparámetros, semilla y umbrales.
4. Exportar cada tabla desde una única ejecución: matrices, AUC e incertidumbre, calibración, validación temporal, tarjetas y utilidad. Separar rendimiento del modelo probabilístico y de la tarjeta de puntos.
5. Regenerar figuras y suplemento; eliminar referencias X/Y y revisar las conclusiones sobre superioridad por subtipo a la luz de los resultados nuevos.

Esta revisión completa las respuestas documentales y la comprobación de los desalineamientos. La reestimación de modelos es el trabajo correctivo pendiente; no se presenta como ya realizada.

## 5. Evidencia y reproducibilidad

- `audit_data.py`: recalcula denominadores, ausencias, tabla basal, comprobaciones aritméticas y pertenencia de predicciones históricas; ejecutar desde el repositorio con el entorno `vpy`.
- `cohort_denominators.csv`, `historical_prediction_cohorts.csv`: prueba cuantitativa del problema de población.
- `missingness_by_variable.csv`: ausencias originales, con grupos y componentes separados; no distingue automáticamente toda ausencia estructural de una no respuesta.
- `baseline_recomputed.csv`: recuentos de referencia; no es una tabla clínica final lista para publicación, especialmente por extremos numéricos y política de ausencias.
- `table5_arithmetic_check_NOT_model_results.csv`: identidades aritméticas usando métricas redondeadas del manuscrito; no resultados nuevos de modelos.
- `comments.json`, `article_text.txt`, `supplement_text.txt`: extracción de los comentarios y localización P de sus anclajes.
- Código contrastado: `src/data_processor.py`, `src/patd_spec_tool.py`, `src/exp_clinical_risk_score.py`, `src/exp_contrast_mining.py`, `src/manuscript_support.py`.
- Históricos contrastados: `out/archive/*_score/clinical_score_threshold_performance.csv`, `clinical_risk_score_per_patient.csv`, HTML de ROC, `data/patD_spec_subset_validation.json` y CSV de auditoría/calibración/temporal de `out/`.

La evidencia local permite identificar estas inconsistencias, pero no certificar ensayos de laboratorio, indicaciones clínicas o ejecuciones que no están conservadas. No se ha realizado una revisión bibliográfica integral ni se atribuyen a la base conclusiones clínicas causales.
