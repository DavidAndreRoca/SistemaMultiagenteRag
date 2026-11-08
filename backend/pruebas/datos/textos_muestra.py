"""Textos ficticios de los PDF de muestra de T09.

Todo es inventado: autores, instituciones, revista, datos, DOI (prefijo de prueba 10.5555)
y referencias. Ninguna persona real participa. Las frases marcadas como ``SOLO_EN_*``
aparecen en una única sección, para comprobar qué se excluye.
"""

from __future__ import annotations

# Frases que solo existen en secciones que deben excluirse (referencias y agradecimientos).
SOLO_EN_REFERENCIAS_ES = "Revista Andina de Psicometría Aplicada"
SOLO_EN_AGRADECIMIENTOS_ES = "Fondo Concursable Ficticio de Investigación"
SOLO_EN_REFERENCIAS_EN = "Journal of Imaginary Sleep Research"
SOLO_EN_AGRADECIMIENTOS_EN = "Fictitious Foundation for Student Wellbeing"

# Bloques: (tipo, texto). Tipos: titulo, autores, afiliacion, seccion, subseccion,
# parrafo, leyenda, tabla (filas separadas por "|" y celdas por ";"), referencia.
Bloques = list[tuple[str, str]]

ARTICULO_ES: Bloques = [
    (
        "titulo",
        "Tutoría entre pares y ansiedad ante la estadística en estudiantes de Psicología"
        " de una universidad privada de Ica",
    ),
    ("autores", "Lucía Mendoza Vargas y Rafael Quispe Huamán"),
    ("afiliacion", "Facultad de Psicología, Universidad Ficticia del Sur, Ica, Perú"),
    ("seccion", "Resumen"),
    (
        "parrafo",
        "La ansiedad ante la estadística es una dificultad frecuente en estudiantes de"
        " Psicología y se asocia con menor rendimiento en los cursos de métodos. El objetivo"
        " de este estudio ficticio fue evaluar el efecto de un programa de tutoría entre pares"
        " sobre la ansiedad ante la estadística en estudiantes de tercer ciclo. Se empleó un"
        " diseño cuasiexperimental con grupo control no equivalente y mediciones antes y"
        " después de la intervención. Participaron 84 estudiantes, 42 en cada grupo. El"
        " programa duró ocho semanas y combinó sesiones semanales de resolución de problemas"
        " con acompañamiento de estudiantes de ciclos superiores. Tras la intervención, el"
        " grupo experimental redujo su puntaje de ansiedad de manera significativa en"
        " comparación con el grupo control, con un tamaño del efecto moderado. Los resultados"
        " sugieren que la tutoría entre pares es una estrategia de bajo costo para disminuir"
        " la ansiedad ante la estadística, aunque se requieren estudios con asignación"
        " aleatoria para confirmar el hallazgo.",
    ),
    (
        "parrafo",
        "Palabras clave: ansiedad ante la estadística, tutoría entre pares, educación"
        " superior, estudiantes de Psicología.",
    ),
    ("seccion", "1. Introducción"),
    (
        "parrafo",
        "Los cursos de estadística forman parte de la formación básica en Psicología porque"
        " permiten comprender, evaluar y producir investigación. Sin embargo, muchos"
        " estudiantes los perciben como una barrera y manifiestan preocupación, tensión y"
        " evitación cuando deben interpretar datos o resolver ejercicios. Este conjunto de"
        " reacciones se ha denominado ansiedad ante la estadística y se distingue de la"
        " ansiedad matemática general porque aparece específicamente frente a tareas de"
        " recolección, análisis e interpretación de datos.",
    ),
    (
        "parrafo",
        "La literatura describe consecuencias académicas relevantes de esta ansiedad. Los"
        " estudiantes con niveles altos tienden a postergar las tareas, a evitar las"
        " consultas con el docente y a obtener calificaciones más bajas. También se ha"
        " observado que la ansiedad reduce la disposición a elegir temas de tesis con"
        " componentes cuantitativos, lo que limita la formación investigadora. Por ello, las"
        " universidades han ensayado distintas intervenciones, entre ellas los talleres de"
        " manejo emocional, el aprendizaje basado en proyectos y la enseñanza con software"
        " estadístico amigable.",
    ),
    (
        "parrafo",
        "La tutoría entre pares ofrece una alternativa atractiva por su bajo costo y por la"
        " cercanía entre el tutor y el estudiante. Un compañero de un ciclo superior que"
        " aprobó el curso puede explicar los conceptos con un lenguaje próximo, normalizar"
        " las dificultades y modelar estrategias de estudio. Diversos trabajos han reportado"
        " mejoras en el rendimiento con esta modalidad, pero la evidencia sobre su efecto en"
        " la ansiedad es menor y procede, en su mayoría, de contextos distintos al peruano.",
    ),
    (
        "parrafo",
        "En el sur del Perú, las universidades privadas reciben estudiantes con trayectorias"
        " escolares diversas y con pocas experiencias previas de análisis de datos. Conocer"
        " si una intervención sencilla reduce la ansiedad ante la estadística puede orientar"
        " decisiones pedagógicas en la región. En consecuencia, el objetivo de este estudio"
        " fue evaluar el efecto de un programa de tutoría entre pares sobre la ansiedad ante"
        " la estadística en estudiantes de Psicología de una universidad privada de Ica. La"
        " hipótesis planteó que el grupo que recibió la tutoría mostraría una reducción mayor"
        " de la ansiedad que el grupo que siguió solo las clases regulares.",
    ),
    ("seccion", "2. Método"),
    ("subseccion", "2.1. Diseño y participantes"),
    (
        "parrafo",
        "Se utilizó un diseño cuasiexperimental con grupo control no equivalente y"
        " mediciones antes y después de la intervención. La población estuvo formada por"
        " los estudiantes matriculados en el curso de Estadística Aplicada del tercer ciclo."
        " Se trabajó con dos secciones intactas del curso: una se asignó al programa de"
        " tutoría y la otra continuó con las clases regulares. La muestra final incluyó 84"
        " estudiantes, 42 en cada grupo, con una edad media de 20,4 años. El 71 % de los"
        " participantes eran mujeres. Ningún estudiante había llevado antes un curso de"
        " estadística en la universidad.",
    ),
    ("subseccion", "2.2. Instrumentos"),
    (
        "parrafo",
        "La ansiedad ante la estadística se midió con una escala ficticia de 24 ítems"
        " construida para este estudio, con cuatro dimensiones: interpretación de"
        " resultados, evaluación en exámenes, solicitud de ayuda y temor al docente. Cada"
        " ítem se respondió en una escala de cinco puntos, desde nada ansioso hasta muy"
        " ansioso, de modo que el puntaje total podía variar entre 24 y 120 puntos. En la"
        " muestra del estudio, la consistencia interna medida con el coeficiente alfa de"
        " Cronbach fue de 0,91 en el pretest y de 0,93 en el postest. Además, se registró el"
        " promedio ponderado del ciclo anterior como variable de control.",
    ),
    ("subseccion", "2.3. Procedimiento"),
    (
        "parrafo",
        "El programa de tutoría duró ocho semanas. Cada semana, los estudiantes del grupo"
        " experimental asistieron a una sesión de noventa minutos dirigida por tutores de"
        " séptimo y noveno ciclo, seleccionados por su rendimiento y capacitados durante"
        " doce horas en estrategias de acompañamiento. Las sesiones combinaron la"
        " resolución guiada de problemas, la discusión de errores frecuentes y breves"
        " ejercicios de respiración antes de las prácticas calificadas. El grupo control"
        " siguió solo las clases regulares del curso. Ambos grupos respondieron la escala"
        " en la primera y en la décima semana del semestre. La participación fue voluntaria"
        " y se obtuvo el consentimiento informado de todos los estudiantes.",
    ),
    ("subseccion", "2.4. Análisis de datos"),
    (
        "parrafo",
        "Se calcularon estadísticos descriptivos para cada grupo y momento de medición. Para"
        " contrastar la hipótesis se aplicó un análisis de covarianza con el puntaje del"
        " postest como variable dependiente, el grupo como factor y el puntaje del pretest y"
        " el promedio ponderado como covariables. Se verificaron los supuestos de"
        " normalidad de los residuos, homogeneidad de varianzas y homogeneidad de las"
        " pendientes de regresión. El tamaño del efecto se estimó con eta cuadrado parcial."
        " El nivel de significación fue de 0,05 y los análisis se realizaron con software"
        " estadístico de libre acceso.",
    ),
    ("seccion", "3. Resultados"),
    (
        "parrafo",
        "En el pretest, ambos grupos presentaron niveles similares de ansiedad ante la"
        " estadística. El grupo experimental obtuvo una media de 78,6 puntos y el grupo"
        " control una media de 77,9 puntos, sin diferencias significativas entre ellos. El"
        " promedio ponderado del ciclo anterior tampoco difirió entre los grupos, lo que"
        " indica que las secciones eran comparables al inicio del semestre.",
    ),
    ("leyenda", "Tabla 1. Puntajes de ansiedad ante la estadística por grupo y momento"),
    (
        "tabla",
        "Grupo;Pretest;Postest|Experimental (n = 42);78,6 (11,2);64,3 (10,8)"
        "|Control (n = 42);77,9 (10,9);75,1 (11,4)",
    ),
    (
        "parrafo",
        "Después de la intervención, la media del grupo experimental descendió a 64,3"
        " puntos, mientras que la del grupo control descendió a 75,1 puntos. El análisis de"
        " covarianza, ajustado por el pretest y por el promedio ponderado, mostró un efecto"
        " significativo del grupo sobre la ansiedad en el postest, F(1, 80) = 18,42,"
        " p < 0,001, con un eta cuadrado parcial de 0,19. Este valor corresponde a un efecto"
        " de magnitud moderada a grande según los criterios convencionales.",
    ),
    (
        "parrafo",
        "Al analizar las dimensiones, la reducción fue mayor en la evaluación en exámenes y"
        " en la solicitud de ayuda. En la dimensión de temor al docente, la diferencia entre"
        " los grupos no alcanzó significación estadística. La asistencia promedio a las"
        " sesiones de tutoría fue de 6,8 sesiones de un total de ocho, y los estudiantes que"
        " asistieron a siete u ocho sesiones mostraron las reducciones más amplias.",
    ),
    (
        "parrafo",
        "Se exploró también si el efecto variaba según el nivel inicial de ansiedad. Para"
        " ello se dividió a los participantes del grupo experimental en dos subgrupos a"
        " partir de la mediana del pretest. Los estudiantes con ansiedad inicial alta"
        " redujeron su puntaje en 17,9 puntos en promedio, mientras que los de ansiedad"
        " inicial baja lo redujeron en 10,7 puntos. Aunque este análisis es exploratorio y"
        " el tamaño de los subgrupos es pequeño, el patrón sugiere que la tutoría beneficia"
        " más a quienes parten de niveles altos de ansiedad.",
    ),
    ("seccion", "4. Discusión"),
    (
        "parrafo",
        "Los resultados apoyan la hipótesis del estudio: el programa de tutoría entre pares"
        " redujo la ansiedad ante la estadística más que las clases regulares. Este hallazgo"
        " coincide con trabajos que destacan el valor de la cercanía entre tutor y"
        " estudiante para crear un ambiente seguro, donde equivocarse no se vive como una"
        " amenaza. La reducción observada en la dimensión de evaluación en exámenes sugiere"
        " que la práctica guiada antes de las evaluaciones fue uno de los componentes más"
        " útiles del programa.",
    ),
    (
        "parrafo",
        "La mejora en la dimensión de solicitud de ayuda también es relevante. Los"
        " estudiantes ansiosos suelen evitar las consultas, lo que agrava sus dificultades."
        " La tutoría ofreció un espacio donde preguntar resultaba natural, y es posible que"
        " esta experiencia haya facilitado la búsqueda de ayuda en otros contextos. En"
        " cambio, el temor al docente no se modificó, lo que puede explicarse porque la"
        " intervención no incluyó cambios en la relación con el profesor del curso.",
    ),
    (
        "parrafo",
        "El mayor beneficio observado en los estudiantes con ansiedad inicial alta tiene"
        " implicaciones prácticas. Si los recursos son limitados, las universidades podrían"
        " identificar al inicio del semestre a los estudiantes más ansiosos mediante una"
        " evaluación breve y ofrecerles la tutoría de manera prioritaria. Esta estrategia"
        " focalizada permitiría concentrar el esfuerzo de los tutores donde el efecto es"
        " mayor, aunque debería evitarse que la selección se perciba como una etiqueta"
        " negativa. Una alternativa es ofrecer la tutoría a todos y animar de forma"
        " especial a quienes obtienen puntajes altos en la evaluación inicial.",
    ),
    (
        "parrafo",
        "El estudio presenta limitaciones que deben considerarse. En primer lugar, el"
        " diseño cuasiexperimental con secciones intactas no permite descartar diferencias"
        " no medidas entre los grupos, aunque ambos fueron equivalentes en el pretest y en"
        " el promedio ponderado. En segundo lugar, la escala de ansiedad se construyó para"
        " este estudio y requiere evidencias adicionales de validez. En tercer lugar, el"
        " seguimiento se limitó al final del semestre, por lo que se desconoce si el efecto"
        " se mantiene en los cursos posteriores.",
    ),
    (
        "parrafo",
        "Pese a estas limitaciones, el estudio aporta evidencia local sobre una estrategia"
        " sencilla y de bajo costo. Las universidades de la región podrían incorporar"
        " programas de tutoría entre pares en los cursos de métodos, con tutores capacitados"
        " y sesiones centradas en la práctica previa a las evaluaciones. Futuras"
        " investigaciones deberían emplear asignación aleatoria, medir el rendimiento"
        " académico como resultado secundario y explorar qué características de los tutores"
        " se asocian con mayores beneficios.",
    ),
    ("seccion", "5. Conclusiones"),
    (
        "parrafo",
        "El programa de tutoría entre pares redujo la ansiedad ante la estadística en"
        " estudiantes de Psicología de una universidad privada de Ica, con un efecto de"
        " magnitud moderada a grande. La reducción fue mayor en la ansiedad asociada a los"
        " exámenes y a la solicitud de ayuda. Estos resultados respaldan la inclusión de la"
        " tutoría entre pares como complemento de las clases regulares en los cursos de"
        " estadística, siempre que se acompañe de una evaluación sistemática de sus efectos.",
    ),
    ("seccion", "Agradecimientos"),
    (
        "parrafo",
        "Este estudio ficticio recibió apoyo del " + SOLO_EN_AGRADECIMIENTOS_ES + ". Los"
        " autores agradecen a los tutores voluntarios por su compromiso con el programa.",
    ),
    ("seccion", "Referencias"),
    (
        "referencia",
        "Arias Pérez, M. y Salas Rojas, J. (2021). Ansiedad ante la estadística en"
        " universitarios: una revisión ficticia. " + SOLO_EN_REFERENCIAS_ES + ", 12(3),"
        " 45-61. https://doi.org/10.5555/rapa.2021.0123",
    ),
    (
        "referencia",
        "Benites Castro, L. (2019). Tutoría entre pares en la educación superior. Editorial"
        " Ficticia del Pacífico.",
    ),
    (
        "referencia",
        "Cárdenas Flores, R., Vílchez Soto, A. y Ramos León, P. (2022). Evitación académica"
        " y rendimiento en cursos de métodos. Revista Ficticia de Educación Superior, 3(1),"
        " 10-25. https://doi.org/10.5555/rfes.2022.0007",
    ),
    (
        "referencia",
        "Delgado Ortiz, S. (2020). Intervenciones para reducir la ansiedad matemática en"
        " universitarios. Cuadernos Imaginarios de Pedagogía, 8(2), 77-90.",
    ),
    (
        "referencia",
        "Espinoza Nuñez, C. y Huamán Ríos, T. (2023). Aprendizaje basado en proyectos en"
        " estadística aplicada. Revista Ficticia de Educación Superior, 4(1), 33-48.",
    ),
]

ARTICULO_EN: Bloques = [
    (
        "titulo",
        "Sleep duration and statistics exam performance among first-year university"
        " students: a fictitious cross-sectional study",
    ),
    ("autores", "Daniel Torres Medina and Ana Huanca Rojas"),
    ("afiliacion", "School of Health Sciences, Fictitious University of the South, Ica, Peru"),
    ("seccion", "Abstract"),
    (
        "parrafo",
        "Insufficient sleep is common among first-year university students and may impair"
        " the cognitive processes required to solve quantitative problems. This fictitious"
        " study examined the association between self-reported sleep duration in the week"
        " before an examination and performance on a statistics midterm exam. A total of 156"
        " first-year students completed a sleep diary for seven nights and a brief"
        " questionnaire on study habits. Students who slept less than six hours per night"
        " obtained lower exam scores than those who slept seven hours or more, after"
        " adjusting for prior academic achievement and weekly study time. The association"
        " followed a dose-response pattern. These findings suggest that sleep hygiene"
        " programs could complement academic support during examination periods, although"
        " longitudinal designs are needed to establish the direction of the effect.",
    ),
    (
        "parrafo",
        "Keywords: sleep duration, academic performance, statistics education, first-year"
        " students.",
    ),
    ("seccion", "1. Introduction"),
    (
        "parrafo",
        "The transition to university brings new academic demands, irregular schedules and"
        " greater autonomy in organizing daily routines. Many first-year students reduce"
        " their sleep to accommodate study, work and social activities, especially in the"
        " days before examinations. Sleep restriction affects attention, working memory and"
        " the consolidation of recently learned material, which are central to solving"
        " statistics problems that require several sequential steps.",
    ),
    (
        "parrafo",
        "Previous research has linked short sleep with lower grade point averages, but most"
        " studies relied on a single retrospective question about usual sleep. Such"
        " measures are prone to recall bias and do not capture the variability that"
        " characterizes examination periods. Daily sleep diaries offer a more precise"
        " estimate and allow researchers to focus on the specific days that precede an"
        " assessment. In addition, few studies have examined performance in quantitative"
        " courses, where the cognitive load of each task is particularly high.",
    ),
    (
        "parrafo",
        "Understanding this association is relevant for universities that offer support"
        " services to first-year students. If shorter sleep before an examination is"
        " associated with poorer performance, sleep education could be added to existing"
        " study skills workshops at a low cost. The aim of this study was therefore to"
        " examine the association between sleep duration in the week before a statistics"
        " midterm exam and exam performance among first-year students, controlling for"
        " prior achievement and weekly study time. We hypothesized that shorter sleep would"
        " be associated with lower exam scores.",
    ),
    (
        "parrafo",
        "A secondary aim was to explore whether the association differed between students"
        " with higher and lower prior achievement. Students who enter university with"
        " weaker quantitative preparation may depend more on effortful reasoning during"
        " the exam and could therefore be more sensitive to the cognitive effects of short"
        " sleep. Alternatively, students with stronger preparation may rely on automated"
        " procedures that are less affected by fatigue. Examining this question can help"
        " support services decide whether sleep education should be offered to all"
        " first-year students or targeted to specific groups.",
    ),
    ("seccion", "2. Methods"),
    ("subseccion", "2.1. Participants"),
    (
        "parrafo",
        "The study used a cross-sectional design. Participants were first-year students"
        " enrolled in an introductory statistics course at a private university. All 190"
        " students enrolled in the course were invited, and 156 provided complete data,"
        " yielding a participation rate of 82 percent. The mean age was 18.7 years and 64"
        " percent of participants were women. Students who reported a diagnosed sleep"
        " disorder were not excluded but were identified for a sensitivity analysis.",
    ),
    ("subseccion", "2.2. Measures"),
    (
        "parrafo",
        "Sleep duration was recorded with a daily sleep diary completed each morning during"
        " the seven days before the midterm exam. Students reported the time they went to"
        " bed, the estimated time they fell asleep and the time they woke up. Average sleep"
        " duration was computed for the seven nights and classified into three categories:"
        " less than six hours, six to less than seven hours, and seven hours or more. Exam"
        " performance was the score on a standardized midterm exam ranging from 0 to 20"
        " points. Prior academic achievement was measured with the admission exam score,"
        " and weekly study time was reported in a brief questionnaire.",
    ),
    ("subseccion", "2.3. Procedure"),
    (
        "parrafo",
        "Students were invited during a regular class two weeks before the midterm exam."
        " Those who agreed to participate received a printed diary and a short explanation"
        " of how to complete it, including examples of common errors such as reporting the"
        " time in bed instead of the time asleep. Research assistants sent a brief reminder"
        " each evening through the course platform. Diaries were returned on the day of the"
        " exam, before the exam started, so that students did not know their scores when"
        " completing the last entry. Exam scores were obtained from the course records"
        " with the written consent of each participant.",
    ),
    ("subseccion", "2.4. Statistical analysis"),
    (
        "parrafo",
        "Descriptive statistics were calculated for all variables. A multiple linear"
        " regression model was fitted with exam score as the outcome and sleep category as"
        " the main predictor, using seven hours or more as the reference category. The"
        " model was adjusted for admission exam score and weekly study time. Assumptions of"
        " linearity, homoscedasticity and normality of residuals were examined graphically."
        " A test for linear trend across sleep categories was also performed. Statistical"
        " significance was set at 0.05, and analyses were conducted with open-source"
        " statistical software.",
    ),
    ("seccion", "3. Results"),
    (
        "parrafo",
        "The average sleep duration in the week before the exam was 6.3 hours. Overall, 48"
        " students slept less than six hours per night, 61 slept between six and seven"
        " hours, and 47 slept seven hours or more. The mean exam score was 12.8 points, with"
        " a standard deviation of 3.1 points. Students in the shortest sleep category"
        " reported more weekly study time than students in the other categories.",
    ),
    (
        "parrafo",
        "In the adjusted regression model, students who slept less than six hours obtained"
        " scores 2.4 points lower than those who slept seven hours or more, with a 95"
        " percent confidence interval from 1.3 to 3.5 points. Students who slept between"
        " six and seven hours obtained scores 1.1 points lower than the reference group,"
        " with a confidence interval from 0.1 to 2.1 points. The test for linear trend was"
        " significant, indicating a dose-response pattern. The model explained 34 percent"
        " of the variance in exam scores.",
    ),
    (
        "parrafo",
        "The sensitivity analysis excluding the nine students with a diagnosed sleep"
        " disorder produced similar estimates. Admission exam score was positively"
        " associated with exam performance, whereas weekly study time showed a weak"
        " association once sleep was taken into account.",
    ),
    (
        "parrafo",
        "When the sample was divided by the median admission exam score, the association"
        " between short sleep and lower exam scores was stronger among students with lower"
        " prior achievement. In this group, students who slept less than six hours scored"
        " 3.1 points below those who slept seven hours or more, compared with 1.6 points in"
        " the group with higher prior achievement. The interaction term did not reach"
        " statistical significance, so this difference should be interpreted with caution"
        " and confirmed in larger samples.",
    ),
    ("seccion", "4. Discussion"),
    (
        "parrafo",
        "This fictitious study found that shorter sleep in the week before a statistics"
        " exam was associated with lower exam performance among first-year students, even"
        " after adjusting for prior achievement and study time. The dose-response pattern"
        " strengthens the plausibility of the association and is consistent with"
        " experimental evidence showing that sleep restriction impairs working memory and"
        " attention, two processes required to solve multistep statistical problems.",
    ),
    (
        "parrafo",
        "An interesting finding was that students who slept less reported more study time."
        " This suggests that some students sacrifice sleep to study, a strategy that may be"
        " counterproductive if the loss of sleep reduces the efficiency of learning and"
        " retrieval during the exam. Support services could therefore emphasize that"
        " adequate sleep is part of effective preparation rather than a competing activity.",
    ),
    (
        "parrafo",
        "The stronger association observed among students with lower prior achievement,"
        " although not statistically conclusive, is consistent with the idea that students"
        " who depend more on effortful reasoning are more vulnerable to the effects of"
        " fatigue. If confirmed, this pattern would suggest that sleep education is"
        " particularly important for students who already face greater academic"
        " challenges, and that it could help to reduce rather than widen existing gaps in"
        " performance during the first year of university.",
    ),
    (
        "parrafo",
        "These results are in line with previous fictitious studies that reported lower"
        " grades among students with short sleep, but they extend that work in two ways."
        " First, sleep was measured with daily diaries in the specific week before an"
        " assessment, which reduces recall bias. Second, the outcome was a standardized"
        " statistics exam rather than an overall grade point average, which allows a more"
        " direct link with the cognitive demands of quantitative problem solving.",
    ),
    (
        "parrafo",
        "Several limitations should be noted. The cross-sectional design does not allow"
        " causal conclusions, and it is possible that students who were struggling with the"
        " course both studied longer and slept less because of anxiety. Sleep was"
        " self-reported, and diaries may still contain estimation errors. The study was"
        " conducted in a single course at one private university, which limits"
        " generalizability to other institutions and disciplines.",
    ),
    (
        "parrafo",
        "Future studies should combine sleep diaries with objective measures such as"
        " actigraphy and follow students across several examination periods. Intervention"
        " studies could test whether brief sleep education sessions improve exam"
        " performance in quantitative courses, and whether the benefits differ according to"
        " prior achievement or anxiety levels.",
    ),
    ("seccion", "5. Conclusion"),
    (
        "parrafo",
        "Shorter sleep in the week before a statistics midterm exam was associated with"
        " lower performance among first-year university students, following a dose-response"
        " pattern. Universities could consider adding sleep education to academic support"
        " programs during examination periods, while longitudinal and experimental studies"
        " clarify the direction of the association.",
    ),
    ("seccion", "Acknowledgments"),
    (
        "parrafo",
        "This fictitious study was supported by the " + SOLO_EN_AGRADECIMIENTOS_EN + ". The"
        " authors thank the course instructors for their help with data collection.",
    ),
    ("seccion", "References"),
    (
        "referencia",
        "Alvarez, P., and Chen, L. (2020). Sleep diaries in university populations: a"
        " fictitious review. " + SOLO_EN_REFERENCIAS_EN + ", 15(2), 101-118."
        " https://doi.org/10.5555/jisr.2020.0042",
    ),
    (
        "referencia",
        "Brown, K. (2018). Working memory and statistical reasoning. Imaginary Press.",
    ),
    (
        "referencia",
        "Garcia, M., Lopez, R., and Smith, J. (2022). Study time, sleep and grades in"
        " first-year students. Fictitious Journal of Higher Education, 9(4), 210-225.",
    ),
    (
        "referencia",
        "Nakamura, Y. (2021). Sleep restriction and problem solving: an imaginary"
        " experiment. Fictitious Journal of Cognitive Science, 7(1), 5-19.",
    ),
]

# Documento corto: tiene una sección IMRaD, pero queda por debajo del umbral de palabras.
DOCUMENTO_CORTO: Bloques = [
    ("titulo", "Nota breve ficticia sobre hábitos de estudio en primer ciclo"),
    ("autores", "Equipo de Investigación Ficticio"),
    ("seccion", "Introducción"),
    (
        "parrafo",
        "Esta nota breve y ficticia describe en pocas líneas los hábitos de estudio de un"
        " grupo de estudiantes de primer ciclo. No presenta métodos ni resultados completos,"
        " por lo que no alcanza la extensión mínima que se espera de un artículo empírico.",
    ),
    (
        "parrafo",
        "Los estudiantes indicaron que estudian sobre todo la noche anterior a las"
        " evaluaciones y que prefieren repasar con compañeros antes que en solitario.",
    ),
]


def documento_sin_secciones() -> Bloques:
    """Texto largo del artículo en español con títulos que no son secciones IMRaD."""
    parrafos = [texto for tipo, texto in ARTICULO_ES if tipo == "parrafo"]
    cuerpo = parrafos[2:-1]  # sin resumen, palabras clave ni agradecimientos
    titulos = ["Primera parte", "Segunda parte", "Tercera parte", "Cuarta parte"]
    bloques: Bloques = [
        ("titulo", "Ensayo ficticio sobre la enseñanza de la estadística"),
        ("autores", "Equipo de Investigación Ficticio"),
    ]
    por_parte = -(-len(cuerpo) // len(titulos))
    for indice, titulo in enumerate(titulos):
        bloques.append(("seccion", titulo))
        bloques += [("parrafo", p) for p in cuerpo[indice * por_parte : (indice + 1) * por_parte]]
    # Se repite el cuerpo para superar con holgura el umbral de palabras.
    bloques.append(("seccion", "Quinta parte"))
    bloques += [("parrafo", p) for p in cuerpo]
    return bloques


TEXTO_ESCANEADO = [
    "Documento ficticio escaneado",
    "",
    "Esta página es solo una imagen: no tiene capa de texto.",
    "Simula un artículo antiguo digitalizado con un escáner.",
    "El canal de extracción debe excluirlo y registrar el motivo.",
]
