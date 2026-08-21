# 📋 Guida: Visualizzazione e Aggiornamento Dashboard Oncologia Concorso

## Situazione Attuale

✅ **Cartella principale (su OneDrive):**
```
~/Library/CloudStorage/OneDrive-UniversitàdegliStudidiUdine/OncologiaConcorso/
```

La struttura è organizzata così:
- **`dashboard/oncologia-concorso.html`** → Pagina HTML del dashboard (il "renderer")
- **`Schede/<Categoria>/*.md`** → File markdown delle singole schede cliniche
- **`data/study-index.json`** → Indice dei trial e degli studi (alimenta il dashboard)
- **`Congressi/Grandangolo/*.pdf`** → Slide e risorse congressuali

---

## 🎯 Come Visualizzare il Dashboard

### Opzione 1: Aprire direttamente sul Mac (✅ Più veloce)
```bash
# Apri il file nel browser predefinito
open ~/Library/CloudStorage/OneDrive-UniversitàdegliStudidiUdine/OncologiaConcorso/dashboard/oncologia-concorso.html
```

Oppure **trascina il file nella barra degli indirizzi di Chrome**.

### Opzione 2: Usare un server locale (per sviluppo)
Se vuoi servire il file via HTTP (utile se modifichi il codice HTML):
```bash
cd ~/Library/CloudStorage/OneDrive-UniversitàdegliStudidiUdine/OncologiaConcorso/
python3 -m http.server 8000
# Poi vai su: http://localhost:8000/dashboard/oncologia-concorso.html
```

---

## 📝 Come Aggiornare le Schede

Le schede cliniche sono **file Markdown** nella cartella `Schede/`. Ecco il workflow:

### 1️⃣ Modifica la scheda `.md`
Apri con qualunque editor (VSCode, iA Writer, TextEdit...):
```
~/Library/CloudStorage/OneDrive-UniversitàdegliStudidiUdine/OncologiaConcorso/Schede/Urologici/Prostata.md
```

**Convenzioni di formattazione** (dal project):
- **`==testo==`** → Evidenziazione verde (enfasi standard)
- **`++testo++`** → Evidenziazione arancione (dati **aggiornati**/verificati)
- **`!!testo!!`** → Evidenziazione ambra (**attenzione**, red flag)
- **`#### Punti chiave`** → Riquadro collassabile a fine sezione
- **Prosa**, non elenchi (tranne per tabelle di classificazione e liste rapide tipo "Errori da evitare")

Esempio:
```markdown
## Epidemiologia

La prostata è il tumore più frequente...

Nel 2024 si stimano ++28.000 nuovi casi++ in Italia (AIOM).

!Attenzione! Il PSA non diagnostica il cancro: confirmare sempre con biopsia.

### Terapia di prima linea

#### Punti chiave
- Ormonoterapia è pillar della terapia
- ADT intensificato con chemio in MHRPC
- ++TALAPRO-2 e EMBARK++ hanno mostrato benefici OS
```

### 2️⃣ Il dashboard legge automaticamente
Quando salvi il file markdown:
1. ✅ OneDrive sincronizza automaticamente
2. ✅ La pagina HTML rileva il `.md` dal "indice" (study-index.json)
3. ✅ Quando clicchi sulla scheda nel sidebar, il dashboard carica e renderizza il markdown in HTML in tempo reale

**Non serve ricompilare nulla!** Il dashboard è un "live renderer" che trasforma il markdown al volo.

---

## 🔄 Sincronizzazione con GitHub

**Situazione attuale:**
- Fonte di verità: **OneDrive** (aggiornamenti clinici)
- Backup/versioning: **GitHub** (cartella `oncologia-concorso-pages`)

**Quando fare un commit su GitHub:**
```bash
cd ~/Documents/oncologia-concorso-pages

# 1. Copia i file aggiornati da OneDrive
cp -r ~/Library/CloudStorage/OneDrive-UniversitàdegliStudidiUdine/OncologiaConcorso/Schede ./
cp -r ~/Library/CloudStorage/OneDrive-UniversitàdegliStudidiUdine/OncologiaConcorso/dashboard ./

# 2. Verifica le differenze
git status

# 3. Aggiungi e commita
git add .
git commit -m "Update schede + verifica letteratura - [data]"
git push
```

---

## 🎨 Struttura del Dashboard HTML

Il file `oncologia-concorso.html` contiene:

**Top section:**
- ✅ CSS completo (tema light/dark automatico)
- ✅ Layout sidebar + main content area
- ✅ Palette colore con system preference detection

**JavaScript highlights:**
- `markdownToHtml()` → Converte markdown → HTML (supporta evidenziazioni custom `++` `!!`)
- `renderMermaid()` → Renderizza diagrammi mermaid nei flowchart
- `renderFlowDiagrams()` → Carica e renderizza i `.flow.json` personalizzati
- Command palette (⌘K) per navigazione veloce

---

## 🚀 Workflow Consigliato

### Per aggiornamenti clinici (routine):
1. Apri il file `.md` della scheda in OneDrive
2. Modifica secondo le convenzioni
3. Salva → OneDrive sincronizza automaticamente
4. Ricarica il browser (F5) per vedere i cambiamenti

### Per aggiornamenti massicci (es. verifica letteratura):
1. Aggiorna tutte le schede in locale
2. Sincronizza OneDrive
3. Testa nel browser (localhost:8000 se serve)
4. Fai commit su GitHub con messaggio descrittivo
5. Aggiorna il `data/study-index.json` se hai aggiunto trial/studi

### Per aggiornamenti del dashboard stesso (HTML/CSS/JS):
1. Modifica `oncologia-concorso.html`
2. Testa con F12 (Dev Tools) nel browser
3. Se è una feature, documentala nei commenti del codice
4. Salva e commit su GitHub

---

## 📚 File Chiave da Conoscere

| File | Scopo |
|------|-------|
| `Schede/*/` | Contenuto clinico markdown (fonte di verità) |
| `dashboard/oncologia-concorso.html` | Pagina web (renderer) |
| `data/study-index.json` | Metadati schede + trial (alimenta sidebar) |
| `Schede/Mammella/mammella-*.flow.json` | Diagrammi di flusso interattivi |

---

## 🐛 Troubleshooting

**P: "Il dashboard non carica i nuovi cambiamenti"**
- R: Premi F5 per hard refresh, o Cmd+Shift+R (Mac)
- Se usi localhost:8000, verifica che il server stia girando

**P: "Il file .md ha errori di formattazione"**
- R: Controlla i doppi spazi, i ritorni a capo prima di liste
- Usa `⌘K` nel dashboard per cercare → vai direttamente alla scheda problematica

**P: "Voglio rendere il dashboard disponibile online"**
- R: Puoi hostare il repository GitHub con GitHub Pages, oppure usare una solution di hosting statico (Vercel, Netlify)
- Basta eseguire push del contenuto su GitHub e attivare Pages

---

## ✨ Prossimi Step Suggeriti

1. **Automatizzare la sincronizzazione GitHub**: Crea uno script che copia da OneDrive → GitHub ogni sera
2. **Aggiungere search**:  Potenzia ⌘K per cercare all'interno dei contenuti markdown
3. **Verifiche letteratura continue**: Crea un sistema per tracciare quali schede hanno bisogno di aggiornamento (data di ultima verifica)

---

📧 Domande? Usa ⌘K nel dashboard per navigare, oppure controlla il `projet` nel Claude project per memo e decisioni passate.
