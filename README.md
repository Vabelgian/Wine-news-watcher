# Wine News Watcher

Surveille des flux RSS de critiques vin (Decanter, Jancis Robinson) + Google
News, filtre par mots-clés (régions, cépages, "millésime"...), et envoie un
digest groupé sur Discord des nouveaux articles pertinents.

Ne reproduit jamais le contenu d'un article : uniquement titre, source et
lien. Le principe est celui d'un lecteur RSS classique — chaque média garde
son trafic, tu cliques pour lire chez eux.

## Mise en place (5 min)

### 1. Créer un salon Discord dédié
Recommandé : un salon séparé du bot de stock, par ex. `#wine-news`, avec son
propre webhook (Salon → ⚙️ Intégrations → Webhooks → Nouveau webhook →
copier l'URL). Voir le premier bot (`wine-stock-watcher`) pour le détail des
étapes si besoin d'un rappel.

### 2. Créer le repo GitHub (ou dossier dans un repo existant)
Pousse tous les fichiers de ce dossier.

### 3. Ajouter le secret GitHub
**Settings → Secrets and variables → Actions → New repository secret** :
- `DISCORD_WEBHOOK_URL` → l'URL du webhook de l'étape 1

### 4. Ajuster les mots-clés (optionnel)
Édite `keywords` dans `config.yaml` selon tes envies (ajouter "Barbera",
"Etna", "Douro"...). Plus la liste est longue, plus tu couvres de sujets —
mais aussi plus de bruit potentiel côté Google News.

### 5. Premier lancement
Onglet **Actions** → "Check wine news" → **Run workflow**. Comme pour le
bot de stock, ce premier run enregistre tous les articles déjà en ligne
comme "déjà vus" — tu ne reçois donc rien la première fois. Les runs
suivants (quotidiens) ne signalent que le nouveau contenu.

## Tester en local

```bash
pip install -r requirements.txt
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/xxx/yyy"
python watcher.py
```

## Notes
- Fréquence : 1x/jour (6h UTC). L'actualité vin ne justifie pas plus
  fréquent, et ça limite le bruit.
- Sources actuelles : Decanter et Jancis Robinson en flux RSS direct
  (filtrés par mot-clé), + une recherche Google News RSS par mot-clé
  (couvre beaucoup plus de médias sans avoir à chercher un flux par site).
- Pas de flux RSS public trouvé chez James Suckling ou Vinous à ce jour —
  Google News devrait tout de même faire remonter leurs articles publics
  s'ils sont indexés.
- `state.json` retient les ~1000 derniers articles vus pour éviter les
  doublons ; committé automatiquement par le workflow.
