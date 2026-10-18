# Traduire l'app Uzima en kiluba

Le fichier `kiluba-a-relire.csv` s'ouvre dans Excel ou LibreOffice (séparateur « ; »). Il contient les
316 textes de l'app patient.

**Pour le traducteur** (idéalement une personne du métier de la santé qui parle kiluba) :

1. Commencez par les lignes **« SANTÉ — en premier »** : avertissements (lots rappelés ou contrefaits,
   ordonnance, urgences, rappels de traitement). Elles n'ont volontairement pas de brouillon.
   Traduisez-les avec soin : une erreur peut mettre un patient en danger.
2. Pour les autres lignes, la colonne « Brouillon kiluba » est une proposition automatique **peu fiable**.
   Corrigez-la ou réécrivez-la.
3. Écrivez la traduction finale dans la colonne **« KILUBA RELU »**. Seule cette colonne sera mise dans l'app.
4. Gardez tel quel tout ce qui est entre accolades : `{prix}`, `{pharmacie}`, `{duree}`… L'app y met
   automatiquement le prix, le nom de la pharmacie, la durée…
5. Ajoutez aussi, sur une ligne à part, la phrase « Choisissez votre langue » en kiluba : elle s'affiche sur le
   premier écran de l'app.

Tant qu'une phrase n'a pas de traduction relue, l'app l'affiche en français.
