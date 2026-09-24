# Procedencia de `foods.json`

- **Fuente**: USDA FoodData Central, distribución **SR Legacy (abril de 2018)**, dominio
  público. Descarga: `https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_sr_legacy_food_csv_2018-04.zip`.
- **Fecha de consulta**: 2026-09-23.
- **Método**: descarga del volcado CSV completo (`food.csv`, `food_nutrient.csv`,
  `nutrient.csv`) en lugar de la API de búsqueda, para obtener valores exactos y evitar los
  límites de peticiones de `DEMO_KEY`. Se extrajeron los nutrientes `Energy` (id 1008,
  kcal), `Protein` (1003), `Total lipid (fat)` (1004), `Carbohydrate, by difference` (1005) y
  `Fiber, total dietary` (1079) por `fdc_id`, y se seleccionaron manualmente ~200 alimentos
  habituales en España cubriendo las 14 categorías de `FoodCategory`. El script de curación
  no se versiona (herramienta puntual); el `fdc_id` de cada alimento permite volver a
  consultar el registro original en <https://fdc.nal.usda.gov/food-details/{fdc_id}/nutrients>.
- **Convención de peso**: los alimentos que habitualmente se cocinan (legumbres, arroz,
  pasta, avena, quinoa, cuscús, harinas) usan el valor **crudo/seco** de USDA, coherente con
  una lista de la compra de ingredientes tal como se compran; el motor no modela mermas ni
  rendimientos de cocción.
- **`energy_note`**: se añade cuando `|kcal − (4·proteína + 4·carbohidratos + 9·grasa)|`
  supera el 12 % de las kcal declaradas. Motivos observados:
  - **Alcohol** (cerveza, vino tinto): USDA computa la energía incluyendo el alcohol
    (~7 kcal/g), que no aparece en las columnas de macronutrientes del contrato.
  - **Fibra alta** (≥ 6 g/100 g: cacao en polvo, frambuesa, haba): el factor calórico de la
    fibra es menor que el genérico de 4 kcal/g usado en la fórmula de verificación.
  - **Factores de Atwater específicos por alimento**: USDA FoodData Central no siempre usa
    los factores genéricos 4-4-9; en alimentos de baja densidad calórica (la mayoría de
    verduras y frutas) una diferencia absoluta pequeña se convierte en una diferencia
    relativa grande. Es el caso más frecuente (la mayoría de las 39 justificaciones).
- **Alérgenos**: derivados de la composición conocida del alimento (gluten en trigo/cebada/
  centeno, frutos secos de árbol en la lista de frutos secos, huevo en huevo/mayonesa, soja
  en derivados de soja/salsa de soja, pescado y marisco en su categoría). El cacahuete es
  legumbre y **no** se etiqueta como `tree_nuts` (el contrato no define un alérgeno de
  cacahuete independiente); quien declare alergia a cacahuete debe excluirlo por
  `excluded_food_ids` (`cacahuete`, `mantequilla_cacahuete`).
- **`diet_types`**: `vegan` se omite en miel, mayonesa, mantequilla y margarina (esta última
  puede llevar sólidos lácteos según la marca; se trata de forma conservadora). El resto de
  alimentos de origen vegetal incluye las cuatro dietas.
