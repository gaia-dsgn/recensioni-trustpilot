# Recensioni Trustpilot — andrei-copy.com

Ogni 6 ore un'azione copia le recensioni da Trustpilot in `recensioni.json`.
I due blocchi Squarespace (bento grid in home e pagina `/recensioni-andrei-pascu`) leggono:
https://gaia-dsgn.github.io/recensioni-trustpilot/recensioni.json

- Prodotto delle recensioni gia' lette: `prodotti.json` (scelto a mano).
- Recensioni nuove: prodotto solo se nominato nel testo, altrimenti `altro`.
- Aggiornamento a mano: tab Actions → "Aggiorna recensioni" → Run workflow.
