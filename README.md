# Estate Feeder
Un bot per la consultazione e ricezione notifiche su ricerche immobiliari su diverse sorgenti dati e in base a preferenze memorizzate dell'utente.

### Sorgenti integrate ad oggi
Immobiliare.it

### Funzionalità
- Ricerca basata su range di prezzo/superficie
- Ricerca dettagliata a livello di quartiere
- Ricerche per più quartieri/città
- Sistema di notifiche (da affinare)

### Come eseguirlo in locale
Creare un bot telegram e inserire il token al posto di "config.token" nel file principale "estate_feeder.py" e installare le librerie in import con pip.
E' richiesto Python 3.x per l'esecuzione.

#### Docker
Posizionarsi nella cartella e digitare:

    docker build -t estatefeeder .
    docker run -d estatefeeder

### Privacy
Nessun dato personale è memorizzato, l'invio della notifica viene fatto sulla base del chat_id.
Le uniche informazioni memorizzate sono i parametri di ricerca dell'utente, eliminabili tramite il comando _/flushdata_
