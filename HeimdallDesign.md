# 🛡️ HEIMDALL – Wächter der digitalen Welt

> *In der nordischen Mythologie bewacht Heimdall die Regenbogenbrücke Bifröst – den einzigen Zugang nach Asgard. HEIMDALL bewacht den Zugang deiner Kinder zur digitalen Welt.*

---

## 1. Vision & Philosophie

HEIMDALL ist mehr als eine Kindersicherung. Es ist ein **Erziehungswerkzeug**, das Bildschirmzeit nicht nur kontrolliert, sondern Kinder dazu motiviert, sich ihre digitale Zeit aktiv zu verdienen. Statt eines reinen Verbotssystems entsteht ein Kreislauf aus **Verantwortung → Belohnung → Selbstregulation**.

### Kernprinzipien

- **Transparenz:** Kinder sehen jederzeit, welche Regeln gelten und warum
- **Motivation statt Frustration:** Aufgaben erledigen → Zeit verdienen → Autonomie erleben
- **Feingranulare Kontrolle:** Nicht alles über einen Kamm scheren – Lern-Apps ≠ TikTok
- **Elternfreundlich:** Komplexe Regeln, einfache Bedienung
- **Intelligent:** KI-gestützte Analysen und natürlichsprachliche Konfiguration

---

## 2. Systemarchitektur – Überblick

```
┌─────────────────────────────────────────────────────────────┐
│                    HEIMDALL CLOUD BACKEND                    │
│                                                             │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌─────────┐ │
│  │  Regel-   │  │   TAN-    │  │  Quest-   │  │ Analytics│ │
│  │  Engine   │  │  System   │  │  Engine   │  │  Engine  │ │
│  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └────┬────┘ │
│        │              │              │              │       │
│  ┌─────┴──────────────┴──────────────┴──────────────┴────┐  │
│  │              Zentrale API (REST / WebSocket)           │  │
│  └──┬──────────────┬───────────────────┬─────────────┬───┘  │
│     │              │                   │             │      │
│  ┌──┴─────────┐ ┌──┴──────┐ ┌─────────┴────────┐   │      │
│  │  LLM-      │ │Kalender-│ │ Benachrichti-    │   │      │
│  │  Service   │ │ Service │ │ gungsdienst      │   │      │
│  └────────────┘ └─────────┘ └──────────────────┘   │      │
└──────────────┬──────────────────────────────────────┤      │
               │                                      │      │
       ┌───────┴───┐                                  │      │
       │  Eltern-  │                                  │      │
       │  Portal   │    ┌─────────────────────────────┴──┐   │
       │  (PWA)    │    │     Mobile App (Flutter UI)    │   │
       └───────────┘    │  Quests · TANs · Chat · Status │   │
                        ├────────────┬───────────────────┤   │
                        │  Method    │    Method         │   │
                        │  Channel   │    Channel        │   │
                        ├────────────┼───────────────────┤   │
                        │  Android   │   iOS Agent       │   │
                        │  Agent     │   (Swift)         │   │
                        │  (Kotlin)  │   FamilyControls  │   │
                        │  Accessib. │   Screen Time API │   │
                        │  Services  │   (Phase 7)       │   │
                        └────────────┴───────────────────┘   │
                                                             │
                        ┌────────────────────────────────────┘
                        │
                  ┌─────┴──────┐
                  │  Windows-  │
                  │  Agent     │
                  │  (Python)  │
                  └────────────┘
```

> **Architektur-Entscheidung: Hybrid Flutter + Native**
>
> Die Mobile-App folgt einem **Hybrid-Ansatz**: Eine gemeinsame Flutter-UI-Schicht für
> Quests, TANs, Chat und Status wird über **Method Channels** mit plattformspezifischen
> nativen Agents verbunden. Die Agents (Kotlin/Swift) handhaben sicherheitskritische
> Funktionen wie App-Blocking und Überwachung, die tiefe OS-Integration erfordern.
> Flutter allein kann Accessibility Services (Android) und FamilyControls (iOS) nicht
> ansprechen – native Implementierung ist hier zwingend.

### Technologie-Stack

| Komponente | Technologie | Begründung |
|---|---|---|
| Backend API | **Python (FastAPI)** | Stefans Expertise, async, schnell |
| Datenbank | **PostgreSQL** + Redis (Cache) | Relational für komplexe Regeln, Redis für Live-Status |
| Eltern-Portal | **React + TypeScript (PWA)** | Offline-fähig, installierbar, responsive |
| Mobile UI | **Flutter (Dart)** | Cross-Platform UI für Kind-App (Quests, TANs, Chat) |
| Android Agent | **Kotlin** (nativ) | Accessibility Services, Device Admin – nicht in Flutter abbildbar |
| iOS Agent | **Swift** (nativ, Phase 7) | FamilyControls / Screen Time API – nur native Swift |
| Method Channels | **Flutter ↔ Kotlin/Swift** | Brücke zwischen Flutter-UI und nativen Agents |
| Windows Agent | **Python + pywin32** | Service-basiert, Group Policy Integration |
| LLM Service | **Claude API (Sonnet)** | Vision-Fähigkeit für Aufgaben-Nachweis |
| Hosting | **Hetzner Cloud** | DSGVO-konform, Stefans bestehende Infrastruktur |
| CI/CD | **GitHub Actions** | Integration mit bestehendem Workflow |

---

## 3. Datenmodell

### 3.1 Entitäten

```
┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│    Family     │──1:n──│    Child      │──1:n──│    Device     │
│              │       │              │       │              │
│ id           │       │ id           │       │ id           │
│ name         │       │ name         │       │ name         │
│ parents[]    │       │ age          │       │ type (AND/WIN/iOS)│
│ settings     │       │ avatar       │       │ child_id     │
│ timezone     │       │ family_id    │       │ status       │
└──────────────┘       └──────┬───────┘       │ coupled_with[]│
                              │               └──────────────┘
                              │
                    ┌─────────┴─────────┐
                    │                   │
              ┌─────┴──────┐     ┌──────┴─────┐
              │  AppGroup   │     │   Quest     │
              │            │     │            │
              │ id         │     │ id         │
              │ name       │     │ name       │
              │ icon       │     │ description│
              │ color      │     │ reward_type│
              │ category   │     │ reward_mins│
              │ apps[]     │     │ tan_groups[]│
              │ risk_level │     │ proof_type │
              │ child_id   │     │ recurrence │
              └────────────┘     │ ai_verify  │
                                 └────────────┘
```

### 3.2 Kern-Entitäten im Detail

#### App-Gruppen (AppGroup)

```yaml
Beispiel-Gruppen für Leo (12):
  - name: "🎮 Gaming"
    apps: [Minecraft, Roblox, Brawl Stars]
    category: entertainment
    risk_level: medium
    
  - name: "📱 Social Media"
    apps: [TikTok, Instagram, Snapchat]
    category: social
    risk_level: high
    
  - name: "📚 Lernen"
    apps: [Anton, Duolingo, Khan Academy]
    category: education
    risk_level: low
    
  - name: "🎬 Streaming"
    apps: [YouTube, Netflix, Disney+]
    category: media
    risk_level: medium
    
  - name: "💬 Kommunikation"
    apps: [WhatsApp, Signal, Telefon]
    category: communication
    risk_level: low
    
  - name: "🔧 System"
    apps: [Einstellungen, Kamera, Uhr]
    category: system
    risk_level: none  # Immer erlaubt
```

#### Zeitregeln (TimeRule)

```yaml
TimeRule:
  id: uuid
  target_type: "device" | "app_group"
  target_id: uuid
  schedule:
    day_types:
      - type: "weekday" | "weekend" | "holiday" | "vacation" | "custom"
        label: "Schultag"  # Optional
    time_windows:
      - start: "06:00"
        end: "08:00"
        note: "Morgens vor der Schule"
      - start: "14:00"
        end: "20:00"
        note: "Nach der Schule"
    daily_limit_minutes: 120
    group_limits:  # Limits pro App-Gruppe innerhalb des Zeitfensters
      - group_id: "gaming"
        max_minutes: 60
      - group_id: "social_media"
        max_minutes: 30
  priority: 10  # Höhere Priorität überschreibt niedrigere
  active: true
```

#### Tagtypen (DayType)

```yaml
DayType-Quellen:
  - Feiertage: API (ferien-api.de / openholidaysapi.org)
  - Schulferien: API (ferien-api.de) → Bundesland: Baden-Württemberg
  - Benutzerdefiniert:
      - "Oma-Tag": Jeden 2. Samstag  # Lockerere Regeln
      - "Lernwoche": Manuell gesetzt  # Strengere Regeln vor Klassenarbeiten
      - "Geburtstag": Jährlich        # Keine Limits
```

---

## 4. Regel-Engine – Das Herzstück

### 4.1 Regelauswertung (Prioritätskaskade)

```
┌─────────────────────────────────────────────┐
│          Aktive TANs (höchste Prio)         │  ← "Leo hat TAN für 30 Min Gaming"
├─────────────────────────────────────────────┤
│     Ausnahmeregeln (z.B. Geburtstag)        │  ← "Heute keine Limits"
├─────────────────────────────────────────────┤
│       Tagtyp-spezifische Regeln             │  ← "Ferien: bis 21 Uhr"
├─────────────────────────────────────────────┤
│         Wochentags-/Wochenendregeln         │  ← "Mo-Fr: max 2h"
├─────────────────────────────────────────────┤
│            Standardregeln (Basis)            │  ← "Grundsätzlich 06-20 Uhr"
└─────────────────────────────────────────────┘
```

### 4.2 Gerätekopplung

Geräte können gekoppelt werden, sodass die Bildschirmzeit **geräteübergreifend** gezählt wird.

```yaml
DeviceCoupling:
  child: "Leo"
  coupled_devices: ["Leo-Handy", "Leo-PC"]
  shared_budget: true  # Gemeinsames Zeitkonto
  rules:
    - "Gesamtzeit auf allen Geräten: max 3h/Tag"
    - "Wechsel zwischen Geräten: Keine Bonuszeit"
    - "Gaming-Gruppe: max 60 Min egal auf welchem Gerät"
```

**Funktionsweise:**

1. Leo startet Minecraft auf dem PC → Timer beginnt (Gruppe: Gaming)
2. Nach 30 Min wechselt er aufs Handy → Backend erkennt Kopplung
3. Gaming-Budget: noch 30 Min übrig (nicht 60 Min neu)
4. Gesamtbudget: ebenfalls korrekt fortgeführt

### 4.3 Beispiel-Konfiguration: Woche von Leo

```yaml
Leo_Regeln:
  Schultag (Mo-Fr, keine Ferien):
    device_window: "06:00-07:30, 14:00-20:00"
    total_limit: 120 min
    groups:
      Gaming:     max 45 min, nur 14:00-20:00
      Social:     max 20 min, nur 16:00-19:00
      Lernen:     unbegrenzt innerhalb device_window
      Streaming:  max 45 min
      Kommunikation: immer erlaubt
      System:     immer erlaubt

  Wochenende (Sa-So):
    device_window: "07:00-21:00"
    total_limit: 180 min
    groups:
      Gaming:     max 90 min
      Social:     max 30 min, nur 10:00-20:00
      Lernen:     unbegrenzt
      Streaming:  max 60 min
      Kommunikation: immer erlaubt

  Ferien:
    device_window: "08:00-21:00"
    total_limit: 210 min
    groups:
      Gaming:     max 120 min
      Social:     max 45 min
      Streaming:  max 90 min

  Feiertag:
    inherit: "Wochenende"  # Erbt Wochenend-Regeln
    override:
      total_limit: 210 min  # Etwas mehr
```

---

## 5. TAN-System – Erweitert & Intelligent

### 5.1 TAN-Typen

```yaml
TAN:
  id: uuid
  code: "HERO-7749"  # Lesbarer Code, thematisch
  type: "time" | "group_unlock" | "extend_window" | "override"
  scope:
    groups: ["gaming"]           # Nur für bestimmte Gruppen (oder leer = alle)
    devices: ["Leo-Handy"]       # Nur für bestimmte Geräte (oder leer = alle)
  value:
    minutes: 30                  # Zusätzliche Minuten
    # ODER
    unlock_until: "21:00"        # Gruppe bis Uhrzeit freischalten
    # ODER
    override_rule: "no_limit"    # Temporär keine Limits
  validity:
    created_at: "2026-02-08T10:00:00"
    expires_at: "2026-02-08T23:59:59"  # Verfällt um Mitternacht
    single_use: true
  source: "quest" | "parent_manual" | "scheduled"
  status: "active" | "redeemed" | "expired"
```

### 5.2 TAN-Regeln & Einschränkungen

```yaml
TAN_Policies:
  max_tans_per_day: 3
  max_bonus_minutes_per_day: 90
  
  group_restrictions:
    social_media:
      tan_allowed: false          # TANs können Social Media NICHT freischalten
      reason: "Grundsätzliche Familienentscheidung"
    gaming:
      tan_allowed: true
      max_bonus_per_day: 60       # Max 60 Min extra durch TANs
    streaming:
      tan_allowed: true
      max_bonus_per_day: 45
  
  blackout_hours:
    - after: "21:00"              # Keine TAN-Einlösung nach 21 Uhr
    - before: "06:00"             # Keine TAN-Einlösung vor 6 Uhr
```

### 5.3 TAN-Einlösung (Flow)

```
Kind öffnet HEIMDALL App
        │
        ▼
[TAN-Code eingeben: HERO-7749]
        │
        ▼
Backend prüft:
  ✓ TAN existiert & aktiv?
  ✓ Noch nicht abgelaufen?
  ✓ Tages-Limit nicht erreicht?
  ✓ Gruppe per TAN erlaubt?
  ✓ Nicht in Blackout-Stunde?
        │
    ┌───┴───┐
    │       │
   OK    ABGELEHNT
    │       │
    ▼       ▼
Timer      Fehlermeldung
startet    "Gaming-TANs sind
           für heute aufgebraucht"
```

---

## 6. Quest-System – Aufgaben & Belohnungen

### 6.1 Quest-Kategorien

```yaml
Quest_Kategorien:
  🏠 Haushalt:
    - name: "Staubsauger-Held"
      description: "Wohnzimmer und Flur saugen"
      reward: 20 min
      tan_groups: ["gaming", "streaming"]
      proof: photo
      ai_verify: true
      recurrence: weekly
      
    - name: "Spülmaschinen-Ninja"
      description: "Spülmaschine ausräumen & einräumen"
      reward: 15 min
      tan_groups: ["gaming", "streaming"]
      proof: parent_confirm
      recurrence: daily
      
    - name: "Wäsche-Meister"
      description: "Wäsche zusammenlegen und einräumen"
      reward: 15 min
      tan_groups: ["gaming", "streaming"]
      proof: photo
      ai_verify: true
      recurrence: weekly

    - name: "Zimmer-Check"
      description: "Eigenes Zimmer aufräumen"
      reward: 20 min
      tan_groups: ["gaming", "streaming"]
      proof: photo
      ai_verify: true
      ai_prompt: "Prüfe ob das Kinderzimmer aufgeräumt ist: Boden frei, Bett gemacht, Schreibtisch ordentlich"
      recurrence: daily

  📚 Schule & Lernen:
    - name: "Hausaufgaben erledigt"
      description: "Alle Hausaufgaben für morgen fertig"
      reward: 25 min
      tan_groups: ["gaming", "streaming", "social_media"]  # Auch Social!
      proof: parent_confirm
      recurrence: school_days
      
    - name: "Mathe-Training"
      description: "20 Minuten Mathe-Arena üben"
      reward: 15 min
      tan_groups: ["gaming"]
      proof: auto  # HEIMDALL erkennt App-Nutzung der Mathe-Arena
      auto_detect:
        app: "mathe-arena"
        min_duration: 20
      recurrence: daily
      
    - name: "Vokabel-Held"
      description: "30 Vokabeln in Duolingo/Phase6"
      reward: 15 min
      tan_groups: ["gaming", "streaming"]
      proof: screenshot
      recurrence: daily

    - name: "Buch-Wurm"
      description: "30 Minuten lesen (echtes Buch!)"
      reward: 20 min
      tan_groups: ["gaming", "streaming"]
      proof: parent_confirm
      recurrence: daily

  🌟 Bonus-Quests (zeitlich begrenzt):
    - name: "Wochen-Champion"
      description: "5 Tage in Folge alle Pflicht-Quests erledigt"
      reward: 60 min  # Jackpot!
      tan_groups: ["gaming", "streaming"]
      proof: auto  # System prüft automatisch
      type: streak
      streak_days: 5
```

### 6.2 Quest-Lifecycle

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ AVAILABLE│───▶│ CLAIMED  │───▶│ PENDING  │───▶│ APPROVED │
│          │    │          │    │ REVIEW   │    │          │
│ Quest    │    │ Kind hat │    │ Nachweis │    │ TAN wird │
│ sichtbar │    │ Quest    │    │ eingerei-│    │ generiert│
│ in App   │    │ angenom- │    │ cht      │    │          │
└──────────┘    │ men      │    └────┬─────┘    └──────────┘
                └──────────┘         │
                                     │ Bei AI-Verify:
                                     ▼
                              ┌──────────────┐
                              │ KI prüft     │
                              │ Foto/Nachweis│
                              │              │
                              │ Confidence   │
                              │ > 80%? ──────┼──▶ Auto-Approve
                              │ < 80%? ──────┼──▶ Eltern-Review
                              └──────────────┘
```

### 6.3 Nachweis-Typen

| Typ | Beschreibung | KI-Prüfung möglich? |
|---|---|---|
| `photo` | Kind macht Foto als Beweis | ✅ Vision-Modell prüft |
| `screenshot` | Screenshot der erledigten Aufgabe | ✅ OCR + Analyse |
| `parent_confirm` | Elternteil bestätigt im Portal | ❌ Manuell |
| `auto` | System erkennt automatisch (App-Nutzung) | ✅ Automatisch |
| `checklist` | Kind hakt Teilschritte ab | ❌ Vertrauensbasis |

---

## 7. LLM-Integration – Der intelligente Kern

### 7.1 Einsatzgebiete

```yaml
LLM_Features:

  # 1. AUFGABEN-VERIFIKATION (Vision)
  photo_verification:
    model: "claude-sonnet-4-5-20250929"
    use_case: "Prüfe eingereichte Fotos auf Plausibilität"
    examples:
      - quest: "Zimmer aufräumen"
        prompt: |
          Analysiere dieses Foto eines Kinderzimmers.
          Prüfe: Ist der Boden weitgehend frei? Ist das Bett gemacht?
          Liegt kein offensichtliches Chaos herum?
          Antworte mit: { "approved": true/false, "confidence": 0-100, "feedback": "..." }
        threshold: 80  # Ab 80% Confidence: Auto-Approve
      
      - quest: "Staubsaugen"
        prompt: |
          Analysiere dieses Foto. Ist ein Staubsauger sichtbar?
          Sieht der Raum frisch gesaugt aus (Teppichstreifen, sauberer Boden)?
          
  # 2. NATÜRLICHSPRACHLICHE REGELN
  natural_language_rules:
    model: "claude-sonnet-4-5-20250929"
    use_case: "Eltern können Regeln in natürlicher Sprache formulieren"
    examples:
      - input: "Leo darf am Wochenende eine Stunde länger spielen"
        output:
          action: "modify_rule"
          child: "Leo"
          day_type: "weekend"
          group: "gaming"
          change: "+60 min"
          
      - input: "Während der Prüfungswoche kein TikTok für beide Kinder"
        output:
          action: "create_exception"
          children: ["Leo", "Tochter"]
          group: "social_media"
          period: "next_week"  # System fragt nach genauem Zeitraum
          access: "blocked"

  # 3. INTELLIGENTE ANALYSEN & EMPFEHLUNGEN
  smart_analytics:
    model: "claude-sonnet-4-5-20250929"
    use_case: "Wöchentliche Zusammenfassungen und Empfehlungen"
    examples:
      - type: "weekly_digest"
        output: |
          📊 Wochenbericht für Leo (KW 06):
          
          Leo hat diese Woche 14,2 Stunden Bildschirmzeit genutzt (+8% vs. Vorwoche).
          Gaming machte 45% aus, Lernen 22%, Streaming 18%.
          
          🌟 Positiv: 4 von 5 Quests erledigt, Mathe-Arena Nutzung um 30% gestiegen.
          ⚠️ Auffällig: YouTube-Nutzung hat sich verdoppelt, vor allem zwischen 18-20 Uhr.
          
          💡 Empfehlung: YouTube in die Streaming-Gruppe verschieben und dort das
          Abendlimit auf 30 Min begrenzen.
          
      - type: "anomaly_detection"
        output: |
          ⚠️ Ungewöhnliches Muster erkannt:
          Leo hat gestern 3x versucht, TikTok nach Sperrzeit zu öffnen.
          Möchtet ihr darüber sprechen oder die Regel anpassen?
          
  # 4. CHATBOT FÜR KINDER
  kid_assistant:
    model: "claude-sonnet-4-5-20250929"
    use_case: "Kinder können HEIMDALL Fragen stellen"
    examples:
      - input: "Wie viel Zeit hab ich noch zum Spielen?"
        output: "Du hast heute noch 35 Minuten Gaming-Zeit übrig. Die läuft um 20:00 Uhr ab. Tipp: Wenn du noch den Quest 'Zimmer-Check' machst, bekommst du 20 Minuten extra! 🎮"
      
      - input: "Warum ist TikTok gesperrt?"
        output: "TikTok ist in der Gruppe 'Social Media' und die ist erst ab 16:00 erlaubt. Es ist jetzt 14:30 – noch 1,5 Stunden! In der Zwischenzeit sind Lernen-Apps und Kommunikation offen. 📚"
```

### 7.2 LLM-Architektur

```
┌─────────────────────────────────────────────┐
│              LLM Service Layer               │
│                                             │
│  ┌─────────────┐  ┌─────────────────────┐   │
│  │ Prompt       │  │ Response Parser     │   │
│  │ Templates    │  │ (JSON Extraction)   │   │
│  └──────┬──────┘  └──────────┬──────────┘   │
│         │                    │               │
│  ┌──────┴────────────────────┴──────────┐   │
│  │         Claude API (Sonnet)           │   │
│  │                                       │   │
│  │  • Vision: Foto-Verifikation          │   │
│  │  • Text: Regelinterpretation          │   │
│  │  • Analysis: Wochenberichte           │   │
│  │  • Chat: Kind-Assistenz               │   │
│  └───────────────────────────────────────┘   │
│                                             │
│  Guardrails:                                │
│  • Max Tokens pro Request: 1000             │
│  • Rate Limiting: 100 req/Tag/Familie       │
│  • Kosten-Tracking pro Familie              │
│  • Kindgerechte Sprache erzwingen           │
│  • Keine persönlichen Daten an LLM senden   │
│    (nur anonymisierte Kontextdaten)         │
└─────────────────────────────────────────────┘
```

---

## 8. Eltern-Portal (PWA)

### 8.1 Dashboard

```
┌─────────────────────────────────────────────────────────────┐
│  🛡️ HEIMDALL                        Familie Mustermann  👤  │
├───────────┬─────────────────────────────────────────────────┤
│           │                                                 │
│ 📊 Dash-  │  ┌─── Leo (Online 📱) ──────────────────────┐  │
│    board  │  │                                           │  │
│           │  │  Heute: 1h 23m / 2h 00m  [████████░░] 69%│  │
│ 👦 Leo    │  │  🎮 Gaming:   32m / 45m                   │  │
│           │  │  📱 Social:    0m / 20m                   │  │
│ 👧 Tochter│  │  📚 Lernen:   28m / ∞                    │  │
│           │  │  🎬 Streaming: 23m / 45m                  │  │
│ ⚙️ Regeln │  │                                           │  │
│           │  │  Aktive TANs: HERO-7749 (🎮 +30m)        │  │
│ 🎫 TANs   │  │  Quests heute: 2/4 erledigt ✅            │  │
│           │  │                                           │  │
│ 🏆 Quests │  └───────────────────────────────────────────┘  │
│           │                                                 │
│ 📈 Analyse│  ┌─── Tochter (Offline 💤) ─────────────────┐  │
│           │  │                                           │  │
│ 🤖 KI     │  │  Heute: 0h 45m / 1h 30m  [████░░░░] 50% │  │
│  Assistent│  │  ...                                      │  │
│           │  └───────────────────────────────────────────┘  │
│           │                                                 │
│           │  ┌─── Quick Actions ─────────────────────────┐  │
│           │  │ [🎫 TAN erstellen] [⏸️ Pause] [💬 Nachricht]│ │
│           │  └───────────────────────────────────────────┘  │
└───────────┴─────────────────────────────────────────────────┘
```

### 8.2 Regel-Editor

```
┌─────────────────────────────────────────────────────────┐
│  Regeln für: Leo                              [+ Neu]   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  💬 Oder sag es einfach:                                │
│  ┌───────────────────────────────────────────────────┐  │
│  │ "Leo darf in den Ferien bis 21:30 Uhr spielen"   │  │
│  └───────────────────────────────────────────────────┘  │
│  [KI-Regel erstellen]                                   │
│                                                         │
│  ── Aktive Regeln ──────────────────────────────────    │
│                                                         │
│  📅 Schultag (Mo-Fr)                    Prio: 10  [✏️]  │
│     Gerät: 06:00-07:30, 14:00-20:00                    │
│     Gesamt: 2h | Gaming: 45m | Social: 20m             │
│                                                         │
│  📅 Wochenende (Sa-So)                  Prio: 10  [✏️]  │
│     Gerät: 07:00-21:00                                  │
│     Gesamt: 3h | Gaming: 90m | Social: 30m             │
│                                                         │
│  🌴 Ferien                               Prio: 20  [✏️]  │
│     Gerät: 08:00-21:00                                  │
│     Gesamt: 3,5h | Gaming: 2h | Social: 45m            │
│                                                         │
│  🎂 Geburtstag (08.05.)                 Prio: 30  [✏️]  │
│     Keine Limits                                        │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 8.3 TAN-Generator

```
┌─────────────────────────────────────────────────────────┐
│  🎫 TAN erstellen                                       │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Für:     [Leo ▼]                                       │
│                                                         │
│  Typ:     ○ Zusätzliche Zeit                            │
│           ○ Gruppe freischalten                         │
│           ○ Zeitfenster verlängern                      │
│                                                         │
│  Gruppen: ☑ 🎮 Gaming                                   │
│           ☐ 📱 Social Media  ⚠️ (per Policy gesperrt)   │
│           ☑ 🎬 Streaming                                │
│                                                         │
│  Dauer:   [30] Minuten                                  │
│                                                         │
│  Gültig:  ○ Nur heute                                   │
│           ○ Bis: [Datum]                                │
│                                                         │
│  ┌─────────────────────────────────────────────┐        │
│  │          TAN: HERO-7749                     │        │
│  │                                             │        │
│  │  🎮 Gaming + 🎬 Streaming                    │        │
│  │  +30 Minuten | Gültig bis heute 23:59       │        │
│  │                                             │        │
│  │  [📋 Kopieren]  [📱 An Leo senden]           │        │
│  └─────────────────────────────────────────────┘        │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 9. Analytics-Engine

### 9.1 Dashboards & Berichte

```yaml
Analytics_Bereiche:

  Echtzeit:
    - Aktuelle Nutzung pro Kind/Gerät/Gruppe
    - Live-Statusanzeige (online/offline/gesperrt)
    - Verbleibende Zeit-Budgets
    - Aktive TANs
    
  Tagesbericht:
    - Gesamtzeit pro Kind
    - Aufschlüsselung nach Gruppen (Pie Chart)
    - Zeitverlauf über den Tag (Heatmap)
    - Gesperrte Zugriffsversuche
    - Erledigte Quests
    
  Wochenbericht:
    - Trend-Vergleich zur Vorwoche
    - Top-Apps nach Nutzungszeit
    - Quest-Completion-Rate
    - TAN-Verbrauch
    - KI-generierte Zusammenfassung & Empfehlungen
    
  Monatsbericht:
    - Langzeittrends (Liniendiagramme)
    - Verhältnis Bildung vs. Unterhaltung
    - Quest-Streaks und Erfolgsquoten
    - Vergleich zwischen Kindern (optional, sensibel)
    - Saisonale Muster (Ferien vs. Schulzeit)
    
  Spezial-Analysen:
    - "Welche App wird am häufigsten nach Sperrzeit versucht?"
    - "Korrelation: Lernen-App-Nutzung ↔ Quest-Erledigung"
    - "Wie verändert sich Gaming-Zeit bei Regelanpassungen?"
    - "TAN-Muster: Wann werden die meisten eingelöst?"
```

### 9.2 Analyse-Visualisierungen

```
┌─────────────────────────────────────────────────────────┐
│  📈 Wochenanalyse: Leo                     KW 06 / 2026 │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Nutzung nach Kategorie          Trend (4 Wochen)      │
│  ┌─────────────────────┐        ┌───────────────────┐  │
│  │     ╭───╮           │        │ 3h ┤  ╱╲           │  │
│  │    ╱ 🎮  ╲ 42%      │        │    ┤ ╱  ╲  ╱╲     │  │
│  │   │Gaming │         │        │ 2h ┤╱    ╲╱  ╲╱╲  │  │
│  │    ╲     ╱          │        │    ┤          ╲ │  │  │
│  │  📚 ╰───╯ 🎬        │        │ 1h ┤           ╲│  │  │
│  │  23%    19%         │        │    ┼──┬──┬──┬──┬─┘  │  │
│  │     📱 8% 💬 8%     │        │    KW3 4  5  6      │  │
│  └─────────────────────┘        └───────────────────┘  │
│                                                         │
│  Tagesverteilung (Heatmap)                              │
│  ┌─────────────────────────────────────────────┐        │
│  │     06  08  10  12  14  16  18  20  22      │        │
│  │ Mo  ░░  ··  ··  ··  ▓▓  ██  ██  ░░  ··     │        │
│  │ Di  ░░  ··  ··  ··  ▓▓  ██  ▓▓  ░░  ··     │        │
│  │ Mi  ░░  ··  ··  ··  ██  ██  ██  ▓▓  ··     │        │
│  │ Do  ░░  ··  ··  ··  ▓▓  ▓▓  ██  ░░  ··     │        │
│  │ Fr  ░░  ··  ··  ··  ██  ██  ██  ██  ··     │        │
│  │ Sa  ░░  ▓▓  ▓▓  ░░  ██  ██  ██  ▓▓  ··     │        │
│  │ So  ░░  ▓▓  ██  ▓▓  ██  ██  ▓▓  ░░  ··     │        │
│  │                                             │        │
│  │ ·· = inaktiv  ░░ = gering  ▓▓ = mittel  ██ = hoch  │ │
│  └─────────────────────────────────────────────┘        │
│                                                         │
│  🤖 KI-Insight:                                         │
│  "Leos Gaming-Zeit ist stabil, aber die YouTube-Nutzung │
│   am Abend hat zugenommen. Die Quest-Rate ist mit 78%   │
│   überdurchschnittlich – das Belohnungssystem wirkt."   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 10. Device Agents – Hybrid-Architektur

### 10.1 Architektur-Prinzip: Flutter UI + Native Agents

Die Mobile-App besteht aus zwei Schichten, die über Flutter Method Channels kommunizieren:

```
┌──────────────────────────────────────────────────────────┐
│                    Flutter UI Layer                       │
│              (einmal schreiben, überall nutzen)           │
│                                                          │
│  ┌────────────┐ ┌──────────┐ ┌────────┐ ┌────────────┐  │
│  │ Quest-     │ │ TAN-     │ │ Status │ │ Kind-      │  │
│  │ Übersicht  │ │ Eingabe  │ │ Screen │ │ Chatbot    │  │
│  └────────────┘ └──────────┘ └────────┘ └────────────┘  │
│  ┌────────────┐ ┌──────────┐ ┌─────────────────────┐    │
│  │ Nachweis-  │ │ Blocking │ │ Verbleibende Zeit   │    │
│  │ Upload     │ │ Overlay  │ │ je Gruppe (Live)    │    │
│  └────────────┘ └──────────┘ └─────────────────────┘    │
│                                                          │
├──────────────────── Method Channels ─────────────────────┤
│                                                          │
│  ┌────────────────────┐    ┌────────────────────────┐    │
│  │   Android Agent    │    │     iOS Agent          │    │
│  │   (Kotlin)         │    │     (Swift)            │    │
│  │                    │    │                        │    │
│  │ • AccessibilitySvc │    │ • FamilyControls       │    │
│  │ • DeviceAdmin      │    │ • Screen Time API      │    │
│  │ • UsageStatsManager│    │ • ManagedSettings      │    │
│  │ • Foreground Svc   │    │ • DeviceActivity       │    │
│  │ • App-Blocking     │    │   Monitor              │    │
│  └────────────────────┘    └────────────────────────┘    │
└──────────────────────────────────────────────────────────┘
```

### 10.2 Flutter Method Channel Interface

```dart
/// Gemeinsames Interface das beide nativen Agents implementieren
abstract class HeimdallAgentBridge {
  /// Aktuelle App im Vordergrund
  Stream<AppUsageEvent> get appUsageStream;
  
  /// Prüfe ob Agent-Berechtigungen erteilt sind
  Future<AgentPermissionStatus> checkPermissions();
  
  /// Fordere benötigte Berechtigungen an
  Future<bool> requestPermissions();
  
  /// Blockiere eine App-Gruppe
  Future<void> blockAppGroup(String groupId);
  
  /// Entsperre eine App-Gruppe (z.B. nach TAN)
  Future<void> unblockAppGroup(String groupId, Duration duration);
  
  /// Aktive App-Nutzungszeit pro Gruppe heute
  Future<Map<String, Duration>> getTodayUsageByGroup();
  
  /// Agent-Heartbeat Status
  Future<AgentHealthStatus> getHealthStatus();
}

/// Platform-spezifische Implementierung via MethodChannel
class AndroidAgentBridge implements HeimdallAgentBridge {
  static const _channel = MethodChannel('de.heimdall/agent');
  // Kotlin-Implementation via Accessibility Service
  // ...
}

class IOSAgentBridge implements HeimdallAgentBridge {
  static const _channel = MethodChannel('de.heimdall/agent');
  // Swift-Implementation via FamilyControls
  // ...
}
```

### 10.3 Android Agent (Kotlin – Nativ)

```yaml
Android_Agent:
  Technologie: Kotlin, Android Accessibility Service
  Rolle: Headless Background Service, angesteuert über Method Channels
  
  Funktionen:
    App-Überwachung:
      - Erkennung der aktiven App (Accessibility Events)
      - UsageStatsManager als Fallback/Validierung
      - Zuordnung zu App-Gruppen
      - Nutzungszeit-Tracking (sekundengenau)
      - Vordergrund/Hintergrund-Erkennung
      
    App-Blocking:
      - Overlay bei gesperrten Apps → Flutter Overlay Screen
      - Friendly Overlay mit verbleibender Zeit & Quest-Hinweis
      - Countdown-Warnung 5 Min vor Ablauf
      
    Kommunikation:
      - Method Channel → Flutter UI (lokale Interaktion)
      - WebSocket zum Backend (Echtzeit-Updates)
      - Offline-Modus mit lokaler Regelkopie (Room DB)
      - Sync bei Verbindung wiederhergestellt
      
    Sicherheit:
      - Device Admin für Deinstallationsschutz
      - Erkennung von VPN/Proxy-Umgehungsversuchen
      - PIN-geschützte Einstellungen
      - Persistent Foreground Notification (Android-Pflicht)
```

### 10.4 iOS Agent (Swift – Nativ, Phase 7)

```yaml
iOS_Agent:
  Technologie: Swift, FamilyControls Framework, Screen Time API
  Rolle: Headless Service, angesteuert über Method Channels
  Status: Phase 7 – nach Stabilisierung von Android & Windows
  
  Voraussetzungen:
    - Apple Developer Account (€99/Jahr)
    - FamilyControls Entitlement beantragen (Apple Review!)
    - Genehmigung durch Apple – NICHT garantiert
    - Nur auf Geräten mit iOS 16+ / verwalteten Familiengruppen
    
  Funktionen (eingeschränkt vs. Android):
    App-Überwachung:
      - DeviceActivityMonitor: App-Nutzung tracken
      - Kategorisierung über ManagedSettings
      - ⚠️ Apple liefert nur App-Kategorien, keine Package-Namen
      - ⚠️ Keine sekundengenaue Echtzeit-Daten wie auf Android
      
    App-Blocking:
      - ManagedSettingsStore: Apps/Kategorien sperren
      - ShieldConfiguration: Custom Blocking-Screen (eingeschränkt)
      - ⚠️ Weniger Kontrolle über Overlay-Design als Android
      
    Was iOS NICHT kann (vs. Android):
      - Kein Accessibility Service → weniger granulare Erkennung
      - Kein Device Admin → Deinstallationsschutz nur über MDM
      - Kein Custom Overlay → nur Apples Shield-UI anpassbar
      - Keine Prozess-Ebene-Kontrolle → nur App-Kategorien
      - VPN/Proxy-Erkennung sehr eingeschränkt
      
  Architektur:
    ┌──────────────────────────────────┐
    │ Flutter UI (identisch mit Android)│
    ├──────── Method Channel ──────────┤
    │ Swift Agent                      │
    │  ├─ FamilyControls              │
    │  │   └─ AuthorizationCenter     │
    │  ├─ DeviceActivityMonitor       │
    │  │   └─ DeviceActivityReport    │
    │  ├─ ManagedSettings             │
    │  │   └─ ShieldConfiguration     │
    │  └─ Screen Time API             │
    │      └─ FamilyActivityReport    │
    └──────────────────────────────────┘
    
  Risiko-Bewertung:
    - Apple kann FamilyControls-Entitlement jederzeit entziehen
    - API-Änderungen bei jedem iOS-Update möglich
    - Deutlich eingeschränkter als Android-Agent
    - Empfehlung: iOS als "Best Effort" kommunizieren,
      nicht als Feature-Parität mit Android versprechen
```

### 10.5 Windows Agent (Python – unverändert, kein Flutter)

```yaml
Windows_Agent:
  Technologie: Python, pywin32, Windows Service
  Hinweis: Kein Flutter – Desktop-Overlay nicht nötig, 
           Blocking über Prozess-Kontrolle + System-Tray-Icon
  
  Funktionen:
    Programm-Überwachung:
      - Win32 API: Aktives Fenster erkennen
      - Prozess-Monitoring (psutil)
      - Browser-Tab-Erkennung (optional, Browser Extension)
      - Nutzungszeit-Tracking
      
    Programm-Blocking:
      - Prozess-Terminierung bei gesperrten Programmen
      - Alternativ: Fenster minimieren + Overlay
      - AppLocker-Integration (Windows Pro)
      - Hosts-File-Manipulation für Website-Blocking
      
    Kommunikation:
      - WebSocket zum Backend + Offline-Fallback
      
    Kind-Interaktion auf Windows:
      - System-Tray-Icon mit Status (verbleibende Zeit)
      - Tray-Menü: TAN eingeben, Quests anzeigen (öffnet PWA)
      - Desktop-Notification bei 5 Min Restzeit
      - Blocking-Screen: Eigenes Fenster (tkinter/webview)
      
    Installation:
      - MSI-Installer mit automatischem Service-Setup
      - Silent Install für einfaches Deployment
      - Auto-Update über Backend
```

### 10.6 Blocking-Overlay Design (Flutter – Cross-Platform)

```
┌──────────────────────────────────┐
│                                  │
│      🛡️ HEIMDALL                 │
│                                  │
│   Minecraft ist gerade pausiert  │
│                                  │
│   Gaming-Zeit für heute:         │
│   45 / 45 Minuten aufgebraucht   │
│                                  │
│   💡 Erledige einen Quest für     │
│      mehr Spielzeit!             │
│                                  │
│   [🏆 Quests anzeigen]           │
│   [🎫 TAN eingeben]              │
│                                  │
└──────────────────────────────────┘

Hinweis: Auf Android als Flutter Overlay gerendert,
auf iOS als Apple ShieldConfiguration (eingeschränkt
anpassbar, Apples Design-Vorgaben gelten).
```

---

## 11. Sicherheit & Datenschutz

### 11.1 DSGVO-Konformität

```yaml
Datenschutz:
  Grundsätze:
    - Datenminimierung: Nur erforderliche Daten erfassen
    - Speicherung auf deutschen Servern (Hetzner)
    - Keine Weitergabe an Dritte
    - Löschkonzept: Nutzungsdaten nach 12 Monaten
    
  LLM-Datenschutz:
    - Keine personenbezogenen Daten an Claude API senden
    - Fotos für Verifikation: Nur temporär verarbeiten, nicht speichern
    - Anonymisierte Prompts: "Kind A" statt "Leo Müller"
    - API-Nutzung über Anthropics EU-Endpoints (wenn verfügbar)
    
  Kinderdaten:
    - Keine Profilerstellung über Inhalte (nur Zeitdaten)
    - Kein Tracking von Nachrichteninhalten
    - Transparente Erklärung für Kinder, was erfasst wird
    
  Technisch:
    - TLS 1.3 für alle Verbindungen
    - Verschlüsselung at Rest (AES-256)
    - JWT-basierte Auth mit Refresh Tokens
    - RBAC: Parent / Child / Admin Rollen
```

### 11.2 Anti-Umgehung

```yaml
Anti_Circumvention:
  Android:
    - Device Admin: Deinstallation nur mit Eltern-PIN
    - Accessibility Service: Neustart bei Deaktivierung
    - Safe Mode Detection
    - Erkennung von Zweit-Profilen
    
  iOS:
    - FamilyControls: An Apple-Familiengruppe gebunden
    - ⚠️ Kein Device Admin → Deinstallationsschutz nur über MDM
    - ⚠️ Kinder können in iOS-Einstellungen Screen Time umgehen
    - Empfehlung: Apple Screen Time zusätzlich aktivieren als Backup
    
  Windows:
    - Protected Service: Standard-User kann nicht stoppen
    - Registry-Schutz für Dienst-Einstellungen
    - Hosts-File-Monitoring
    - Erkennung von Proxy-/VPN-Tools
    
  Allgemein:
    - Heartbeat: Agent meldet sich alle 60s
    - Ausbleiben → Push-Benachrichtigung an Eltern
    - Tamper-Detection → Automatische Geräte-Sperre
```

---

## 12. Entwicklungsplan – Phasen

```
Phasen-Übersicht (Timeline)

Phase 1 ████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░  Foundation
Phase 2 ░░░░░░░░░░░░████████░░░░░░░░░░░░░░░░░░░░  Quest-System + Flutter UI
Phase 3 ░░░░░░░░░░░░░░░░░░░░██████░░░░░░░░░░░░░░  LLM-Integration
Phase 4 ░░░░░░░░░░░░░░░░░░░░░░░░░░████████████░░  Android Agent (Kotlin)
Phase 5 ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░████████  Windows Agent
Phase 6 ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░████  Analytics & Polish
Phase 7 ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  iOS Agent (wenn stabil)
        ├──────┤──────┤──────┤──────┤──────┤──────┤
        Monat 1  M2     M3     M4     M5     M6+
```

### Phase 1: Foundation (4-6 Wochen) 🏗️

```
Ziel: Backend + Eltern-Portal als Standalone neben Salfeld

[ ] FastAPI Backend mit Auth & Familien-Management
[ ] PostgreSQL Datenmodell aufsetzen
[ ] Eltern-Portal (PWA) – Dashboard & Regel-Editor
[ ] App-Gruppen verwalten
[ ] Zeitregeln (Basis) – Tagtyp, Zeitfenster, Limits
[ ] TAN-System (Basis) – Erstellen, Anzeigen, Invalidieren
[ ] Ferien-/Feiertags-API Integration (Baden-Württemberg)
```

**Ergebnis:** Portal funktioniert, TANs werden manuell in Salfeld übertragen.

### Phase 2: Quest-System + Flutter Kind-App (4-5 Wochen) 🏆📱

```
Ziel: Kinder-Interface als Flutter-App, Quest-Engine im Backend

Backend:
[ ] Quest-Engine: Erstellen, Zuweisen, Lifecycle
[ ] Nachweis-Upload Endpoint (Fotos)
[ ] Eltern-Review-Workflow
[ ] TAN-Generierung bei Quest-Abschluss
[ ] Streak-System & Bonus-Quests

Flutter App (Kind-UI, noch OHNE nativen Agent):
[ ] Flutter-Projekt Setup (Android + iOS Targets)
[ ] Login / Kind-Authentifizierung
[ ] Quest-Übersicht & Quest-Annahme
[ ] Nachweis-Upload (Kamera / Galerie)
[ ] TAN-Anzeige & TAN-Eingabe
[ ] Status-Screen: Verbleibende Zeit je Gruppe
[ ] Push-Notifications (Firebase Cloud Messaging)

Warum Flutter jetzt schon?
→ Die Kind-App wird als "reines UI" ohne nativen Agent gestartet.
   Quests, TANs und Status funktionieren sofort – App-Blocking
   übernimmt weiterhin Salfeld. So wird die Flutter-Basis gelegt,
   auf der in Phase 4 der native Android Agent aufbaut.
```

**Ergebnis:** Kinder haben eine eigene App für Quests & TANs. Salfeld läuft noch parallel.

### Phase 3: LLM-Integration (2-3 Wochen) 🤖

```
[ ] Claude API Integration
[ ] Foto-Verifikation für Quests (Vision)
[ ] Natürlichsprachlicher Regel-Editor (Eltern-Portal)
[ ] Wöchentliche KI-Berichte
[ ] Kind-Chatbot in Flutter App ("Wie viel Zeit hab ich noch?")
```

**Ergebnis:** Intelligente Automatisierung, KI-Foto-Check, Chatbot.

### Phase 4: Android Agent – Kotlin Native (5-7 Wochen) 🤖📱

```
Ziel: Nativer Android Agent als Hintergrund-Service,
      verbunden über Method Channels mit der bestehenden Flutter-App

Kotlin Agent (nativ):
[ ] Android Accessibility Service implementieren
[ ] UsageStatsManager Integration
[ ] App-Erkennung & Zuordnung zu App-Gruppen
[ ] Nutzungszeit-Tracking (sekundengenau)
[ ] App-Blocking: Overlay-Trigger an Flutter
[ ] Device Admin für Deinstallationsschutz
[ ] Foreground Service mit Persistent Notification
[ ] Offline-Regelkopie (Room Database)
[ ] WebSocket-Kommunikation mit Backend
[ ] Heartbeat & Tamper Detection

Flutter Integration:
[ ] Method Channel Bridge: Kotlin ↔ Flutter
[ ] HeimdallAgentBridge Interface implementieren
[ ] Blocking-Overlay Screen in Flutter
[ ] Live-Nutzungsanzeige aus Agent-Daten
[ ] TAN-Einlösung → Agent entsperrt Gruppe in Echtzeit
[ ] Berechtigungs-Setup-Wizard (Accessibility, Device Admin, etc.)
[ ] Umfangreiche Tests mit echten Geräten (Leo & Tochter)

Übergangsphase:
[ ] Parallelbetrieb: HEIMDALL + Salfeld (2 Wochen Testphase)
[ ] Salfeld deaktivieren wenn stabil
```

**Ergebnis:** HEIMDALL ersetzt Salfeld auf Android-Geräten.

### Phase 5: Windows Agent (3-4 Wochen) 💻

```
[ ] Python Windows Service
[ ] Programm-Überwachung & Blocking
[ ] System-Tray-Icon mit Status & TAN-Eingabe (öffnet PWA)
[ ] Browser-Integration (optional, Extension)
[ ] WebSocket + Offline-Sync
[ ] Desktop-Notifications
[ ] MSI-Installer
```

**Ergebnis:** Salfeld komplett ablösen auf allen Geräten.

### Phase 6: Analytics & Polish (2-3 Wochen) 📊

```
[ ] Echtzeit-Dashboard im Eltern-Portal
[ ] Tages-/Wochen-/Monatsberichte
[ ] Heatmaps & Trend-Visualisierungen
[ ] KI-Insights & Anomalie-Erkennung
[ ] Gerätekopplung (geräteübergreifende Budgets, Android + Windows)
[ ] Push-Benachrichtigungen
[ ] Feinschliff UI/UX (Flutter + PWA)
```

**Ergebnis:** Vollständiges System live & polished.

### Phase 7: iOS Agent – Swift Native (6-8 Wochen) 🍎

```
⚠️ ERST starten wenn Phase 1-6 stabil laufen!

Vorbereitungen:
[ ] Apple Developer Account (€99/Jahr)
[ ] FamilyControls Entitlement beantragen bei Apple
[ ] ⏳ Apple Review abwarten (kann Wochen/Monate dauern!)
[ ] Genehmigung erhalten? → Weiter. Abgelehnt? → iOS-Plan B (siehe unten)

Swift Agent (nativ):
[ ] FamilyControls AuthorizationCenter: Familien-Genehmigung einholen
[ ] DeviceActivityMonitor: App-Nutzung tracken
[ ] ManagedSettingsStore: Apps/Kategorien sperren
[ ] ShieldConfiguration: Blocking-Screen anpassen
[ ] DeviceActivityReport: Nutzungsdaten für Analytics
[ ] Method Channel Bridge: Swift ↔ Flutter

Flutter Integration:
[ ] IOSAgentBridge implementieren
[ ] Platform-Detection: Android- vs. iOS-Agent laden
[ ] iOS-spezifische Einschränkungen im UI kommunizieren
[ ] TestFlight Beta mit Familie testen

Feature-Parität-Mapping (was geht, was nicht):
  ✅ App-Kategorien sperren/freigeben
  ✅ Zeitlimits pro Kategorie
  ✅ Nutzungsberichte (tageweise)
  ⚠️ Nur App-Kategorien, nicht einzelne Apps blockierbar
  ⚠️ Kein sekundengenaues Tracking (nur Tagesberichte)
  ⚠️ Blocking-Screen weniger anpassbar (Apple Shield)
  ❌ Kein Device Admin / Deinstallationsschutz
  ❌ Kein VPN/Proxy-Detection
  ❌ Kein Custom Overlay (nur Apple-konformes Shield)

Plan B (bei Apple-Ablehnung):
  → Flutter-App ohne nativen Agent als "Companion App"
  → Quests, TANs, Chat, Status funktionieren trotzdem
  → App-Blocking über Apple Screen Time (manuell durch Eltern)
  → HEIMDALL liefert Empfehlungen, Apple Screen Time setzt um
```

**Ergebnis:** iOS-Unterstützung mit bestmöglicher Feature-Abdeckung.

---

## 13. Technische Umsetzungsdetails

### 13.1 API-Design (Auszug)

```yaml
Endpoints:

  # Auth
  POST   /auth/login
  POST   /auth/refresh
  
  # Familien
  GET    /families/{id}
  PUT    /families/{id}/settings
  
  # Kinder
  GET    /families/{id}/children
  POST   /families/{id}/children
  
  # Geräte
  GET    /children/{id}/devices
  POST   /children/{id}/devices
  PUT    /devices/{id}/coupling
  
  # App-Gruppen
  GET    /children/{id}/app-groups
  POST   /children/{id}/app-groups
  PUT    /app-groups/{id}/apps          # Apps hinzufügen/entfernen
  
  # Zeitregeln
  GET    /children/{id}/rules
  POST   /children/{id}/rules
  PUT    /rules/{id}
  POST   /rules/parse-natural           # LLM: Natürliche Sprache → Regel
  
  # TANs
  GET    /children/{id}/tans
  POST   /children/{id}/tans/generate
  POST   /tans/{code}/redeem            # Agent löst TAN ein
  
  # Quests
  GET    /children/{id}/quests
  POST   /families/{id}/quest-templates
  POST   /quests/{id}/claim             # Kind nimmt Quest an
  POST   /quests/{id}/submit-proof      # Nachweis hochladen
  POST   /quests/{id}/review            # Eltern-Review
  
  # Analytics
  GET    /children/{id}/analytics/realtime
  GET    /children/{id}/analytics/daily?date=
  GET    /children/{id}/analytics/weekly?week=
  GET    /children/{id}/analytics/monthly?month=
  GET    /children/{id}/analytics/ai-summary?period=
  
  # Device Agent
  WS     /agent/connect                 # WebSocket für Echtzeit
  POST   /agent/heartbeat
  POST   /agent/usage-event             # App geöffnet/geschlossen
  GET    /agent/rules/current           # Aktuelle Regeln abrufen
  
  # LLM
  POST   /ai/verify-photo              # Quest-Foto prüfen
  POST   /ai/chat                      # Kind-Chatbot
  POST   /ai/generate-report           # Wochenbericht generieren
```

### 13.2 Datenbank-Schema (Kern)

```sql
-- Familien & Benutzer
CREATE TABLE families (
    id UUID PRIMARY KEY,
    name VARCHAR(100),
    timezone VARCHAR(50) DEFAULT 'Europe/Berlin',
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE users (
    id UUID PRIMARY KEY,
    family_id UUID REFERENCES families(id),
    name VARCHAR(100),
    role VARCHAR(20) CHECK (role IN ('parent', 'child')),
    email VARCHAR(255),
    avatar_url TEXT,
    age INTEGER,
    pin_hash VARCHAR(255),  -- Für Kinder: App-PIN
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Geräte
CREATE TABLE devices (
    id UUID PRIMARY KEY,
    child_id UUID REFERENCES users(id),
    name VARCHAR(100),
    type VARCHAR(20) CHECK (type IN ('android', 'windows', 'ios')),
    device_identifier VARCHAR(255) UNIQUE,
    status VARCHAR(20) DEFAULT 'active',
    last_seen TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE device_couplings (
    id UUID PRIMARY KEY,
    child_id UUID REFERENCES users(id),
    device_ids UUID[] NOT NULL,
    shared_budget BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- App-Gruppen
CREATE TABLE app_groups (
    id UUID PRIMARY KEY,
    child_id UUID REFERENCES users(id),
    name VARCHAR(100),
    icon VARCHAR(10),
    color VARCHAR(7),
    category VARCHAR(50),
    risk_level VARCHAR(20) DEFAULT 'medium',
    always_allowed BOOLEAN DEFAULT FALSE,
    tan_allowed BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE app_group_apps (
    id UUID PRIMARY KEY,
    group_id UUID REFERENCES app_groups(id),
    app_package VARCHAR(255),       -- Android: com.example.app
    app_executable VARCHAR(255),    -- Windows: app.exe
    app_name VARCHAR(100),
    platform VARCHAR(20)
);

-- Zeitregeln
CREATE TABLE time_rules (
    id UUID PRIMARY KEY,
    child_id UUID REFERENCES users(id),
    name VARCHAR(100),
    target_type VARCHAR(20) CHECK (target_type IN ('device', 'app_group')),
    target_id UUID,  -- device_id oder app_group_id
    day_types TEXT[] DEFAULT '{"weekday"}',
    time_windows JSONB NOT NULL,     -- [{start, end, note}]
    daily_limit_minutes INTEGER,
    group_limits JSONB DEFAULT '[]', -- [{group_id, max_minutes}]
    priority INTEGER DEFAULT 10,
    active BOOLEAN DEFAULT TRUE,
    valid_from DATE,
    valid_until DATE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tagtypen
CREATE TABLE day_type_overrides (
    id UUID PRIMARY KEY,
    family_id UUID REFERENCES families(id),
    date DATE NOT NULL,
    day_type VARCHAR(50),  -- 'holiday', 'vacation', 'birthday', 'custom'
    label VARCHAR(100),
    source VARCHAR(50),    -- 'api', 'manual'
    UNIQUE(family_id, date)
);

-- TANs
CREATE TABLE tans (
    id UUID PRIMARY KEY,
    child_id UUID REFERENCES users(id),
    code VARCHAR(20) UNIQUE NOT NULL,
    type VARCHAR(30) NOT NULL,
    scope_groups UUID[],
    scope_devices UUID[],
    value_minutes INTEGER,
    value_unlock_until TIME,
    expires_at TIMESTAMPTZ NOT NULL,
    single_use BOOLEAN DEFAULT TRUE,
    source VARCHAR(20),    -- 'quest', 'parent_manual', 'scheduled'
    source_quest_id UUID,
    status VARCHAR(20) DEFAULT 'active',
    redeemed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Quests
CREATE TABLE quest_templates (
    id UUID PRIMARY KEY,
    family_id UUID REFERENCES families(id),
    name VARCHAR(100),
    description TEXT,
    category VARCHAR(50),
    reward_minutes INTEGER,
    tan_groups UUID[],
    proof_type VARCHAR(20),
    ai_verify BOOLEAN DEFAULT FALSE,
    ai_prompt TEXT,
    recurrence VARCHAR(30),  -- 'daily', 'weekly', 'school_days', 'once'
    auto_detect_app VARCHAR(255),
    auto_detect_minutes INTEGER,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE quest_instances (
    id UUID PRIMARY KEY,
    template_id UUID REFERENCES quest_templates(id),
    child_id UUID REFERENCES users(id),
    status VARCHAR(20) DEFAULT 'available',
    -- 'available','claimed','pending_review','approved','rejected','expired'
    claimed_at TIMESTAMPTZ,
    proof_url TEXT,
    proof_type VARCHAR(20),
    ai_result JSONB,  -- {approved, confidence, feedback}
    reviewed_by UUID REFERENCES users(id),
    reviewed_at TIMESTAMPTZ,
    generated_tan_id UUID REFERENCES tans(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Nutzungsdaten
CREATE TABLE usage_events (
    id UUID PRIMARY KEY,
    device_id UUID REFERENCES devices(id),
    child_id UUID REFERENCES users(id),
    app_package VARCHAR(255),
    app_group_id UUID REFERENCES app_groups(id),
    event_type VARCHAR(20),  -- 'start', 'stop', 'blocked'
    started_at TIMESTAMPTZ,
    ended_at TIMESTAMPTZ,
    duration_seconds INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indizes für Analytics
CREATE INDEX idx_usage_child_date ON usage_events (child_id, started_at);
CREATE INDEX idx_usage_group_date ON usage_events (app_group_id, started_at);
CREATE INDEX idx_tans_child_status ON tans (child_id, status);
CREATE INDEX idx_quests_child_status ON quest_instances (child_id, status);
```

---

## 14. Monetarisierung (Optional / Langfristig)

Falls HEIMDALL irgendwann über den Eigenbedarf hinauswächst:

```yaml
Modelle:
  Free_Tier:
    - 1 Kind, 2 Geräte
    - Basis-Zeitregeln
    - 3 Quests/Tag
    - Wochenbericht (ohne KI)
    
  Family (€4,99/Monat):
    - Bis 4 Kinder, unlimited Geräte
    - Alle Regeltypen inkl. Tagtypen
    - Unbegrenzte Quests
    - TAN-System komplett
    - KI-Berichte & Foto-Verifikation
    - Gerätekopplung
    
  Family_Plus (€7,99/Monat):
    - Alles aus Family
    - Natürlichsprachlicher Regel-Editor
    - Kind-Chatbot
    - Erweiterte Analytics
    - Priority Support
    
  Kosten-Kalkulation (pro Familie/Monat):
    - Hetzner: ~€5 (shared, skaliert)
    - Claude API: ~€1-3 (abhängig von Nutzung)
    - Domain/SSL: ~€1
    - Gesamt: ~€7-9 → Ab Family-Tier profitabel
```

---

## 15. Projektname & Branding

```
    ╔═══════════════════════════════════════╗
    ║                                       ║
    ║        🛡️  H E I M D A L L            ║
    ║                                       ║
    ║     Wächter der digitalen Welt        ║
    ║                                       ║
    ╚═══════════════════════════════════════╝

Farbschema:
  Primary:    #4F46E5 (Indigo)    → Vertrauen, Sicherheit
  Secondary:  #10B981 (Emerald)   → Belohnung, Erfolg
  Accent:     #F59E0B (Amber)     → Warnung, Aufmerksamkeit
  Dark:       #1E1B4B (Deep Navy) → Professionell
  
Icon-Konzept:
  Stilisiertes Schild mit einem Auge (Heimdalls allsehendes Auge)
  Modern, freundlich, nicht bedrohlich
  
Namensherkunft:
  Heimdall – Der Wächter der Götter in der nordischen Mythologie.
  Er bewacht Bifröst, die Regenbogenbrücke nach Asgard.
  Er sieht und hört alles, schläft nie, und braucht weniger
  Schlaf als ein Vogel. Perfekte Metapher für ein System,
  das den digitalen Zugang bewacht – fair, aufmerksam und
  unbestechlich.
  
TAN-Code-Schema:
  Format: WORT-ZAHL (z.B. HERO-7749, ODIN-3382, THOR-1156)
  Inspiriert von nordischer Mythologie → Macht Spaß für Kinder!
```

---

## 16. Risiken & Mitigationen

| Risiko | Schwere | Mitigation |
|---|---|---|
| Android API-Änderungen brechen Agent | Hoch | Abstraktionsschicht via Method Channels, schnelle Updates, Beta-Tests |
| Apple lehnt FamilyControls Entitlement ab | Hoch | Plan B: Companion App ohne Agent, Blocking über Apple Screen Time |
| iOS API-Einschränkungen zu restriktiv | Mittel | Feature-Parität nicht versprechen, iOS als "Best Effort" kommunizieren |
| Flutter ↔ Native Bridge instabil | Mittel | Sauberes Interface-Design, umfangreiche Integration-Tests, Fehler-Fallbacks |
| Kinder umgehen System (Factory Reset) | Mittel | Device Admin (Android), Heartbeat-Monitoring, Eltern-Alert |
| LLM-Kosten skalieren unerwartet | Mittel | Rate Limits, Caching, günstigeres Modell als Fallback |
| Foto-Verifikation unzuverlässig | Niedrig | Confidence-Threshold, Eltern-Fallback bei Unsicherheit |
| Kinder empfinden System als unfair | Mittel | Transparente Regeln, Kind-Chat, Belohnungsfokus |
| Scope Creep / Nie fertig | Hoch | Strikte Phasen, MVP first, Salfeld als Backup, iOS erst Phase 7 |
| Flutter-Updates brechen Method Channels | Niedrig | Channel-API ist stabil, Pinned Flutter-Versionen, CI-Tests |

---

## Nächster Schritt

> **Empfehlung:** Starte mit Phase 1 – einem GitHub-Repository `heimdall`, FastAPI-Backend, und dem Eltern-Portal als PWA. In Phase 2 kommt die Flutter Kind-App dazu, die sofort für Quests und TANs nutzbar ist – noch ohne nativen Agent, während Salfeld parallel weiterläuft. Der native Kotlin-Agent dockt in Phase 4 über Method Channels an die bestehende Flutter-App an. iOS kommt frühestens in Phase 7, wenn alles andere stabil ist.

```bash
# Let's go! 🛡️
mkdir heimdall
cd heimdall
git init
# Monorepo-Struktur
mkdir -p backend/app          # FastAPI
mkdir -p frontend/web         # Eltern-Portal (React PWA)
mkdir -p mobile/lib           # Flutter Kind-App
mkdir -p mobile/android/agent # Kotlin Native Agent
mkdir -p mobile/ios/agent     # Swift Native Agent (Phase 7)
mkdir -p agents/windows       # Python Windows Agent
# Der Wächter erwacht...
```
