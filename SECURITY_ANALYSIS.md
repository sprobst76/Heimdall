# Heimdall - Datensicherheitsanalyse

## 1. Datenklassifizierung nach Schutzbedarf

### Kritisch (höchster Schutzbedarf)

| Daten | Risiko | Schutzmaßnahme | Aufwand | Performance | Datenverlust-Risiko |
|-------|--------|---------------|---------|-------------|---------------------|
| **TAN-Codes** | Hoch (Missbrauch möglich) | Client-seitige Verschlüsselung + kurzlebige Gültigkeit | Mittel (3-5 Tage) | Minimal (±5%) | Mittel (Familien-Key nötig) |
| **Nutzungsdaten** (welche Apps, wie lange) | Hoch (Privatsphäre) | Aggregierte Hashes statt Rohdaten | Niedrig (1-2 Tage) | Minimal (±2%) | Kein (rekonstruierbar) |
| **Quest-Nachweise** (Fotos) | Hoch (persönliche Daten) | Zero-Knowledge Proofs oder sofortige Löschung nach Verifikation | Hoch (1-2 Wochen) | Mittel (±15-20%) | Kein (nur temporär) |

### Wichtig (hoher Schutzbedarf)

| Daten | Risiko | Schutzmaßnahme | Aufwand | Performance | Datenverlust-Risiko |
|-------|--------|---------------|---------|-------------|---------------------|
| **App-Gruppen** | Mittel (Regelumgehung) | Familien-spezifische Verschlüsselung | Mittel (2-3 Tage) | Minimal (±3%) | Mittel (Key nötig) |
| **Zeitregeln** | Mittel (Regelumgehung) | Client-seitige Speicherung mit Sync | Niedrig (1 Tag) | Kein Einfluss | Hoch (lokaler Verlust) |
| **Geräte-IDs** | Mittel (Tracking) | Hashing + Salting | Niedrig (1 Tag) | Kein Einfluss | Kein |

### Standard (normaler Schutzbedarf)

| Daten | Risiko | Schutzmaßnahme | Aufwand | Performance | Datenverlust-Risiko |
|-------|--------|---------------|---------|-------------|---------------------|
| **Familien-Metadaten** | Niedrig | Standard-DB-Verschlüsselung | Gering (included) | Kein Einfluss | Kein |
| **Analyse-Daten** | Niedrig | Aggregation vor Speicherung | Gering (included) | Kein Einfluss | Kein |

## 2. Risikoanalyse

### Datenverlust-Szenarien

1. **Familien-Key Verlust**:
   - **Auswirkung**: Alle verschlüsselten Daten (TANs, App-Gruppen) unlesbar
   - **Wahrscheinlichkeit**: Mittel (abhängig von Key-Management)
   - **Recovery**: Nur mit Backup-Key oder Admin-Zugriff möglich

2. **Nutzerpasswort vergessen**:
   - **Auswirkung**: Kein Zugriff auf Key-Derivation möglich
   - **Wahrscheinlichkeit**: Hoch (typisches Nutzerverhalten)
   - **Recovery**: Passwort-Reset mit Key-Neugenerierung nötig

3. **Zero-Knowledge Proof Fehler**:
   - **Auswirkung**: Falsche Quest-Verifikation
   - **Wahrscheinlichkeit**: Niedrig (bei guter Implementierung)
   - **Recovery**: Manuelle Überprüfung nötig

## 3. Empfohlene Schutzstrategie

### Phase 1: Grundschutz (Aufwand: 3-5 Tage, Performance: ±5%)

```python
# 1. TAN-Verschlüsselung
class TAN(Base):
    code_encrypted = Column(String)  # AES-256-GCM
    iv = Column(String)  # 12 Byte IV
    key_version = Column(Integer)  # Für Key-Rotation

# 2. App-Gruppen Verschlüsselung
class AppGroup(Base):
    name_encrypted = Column(String)
    apps_encrypted = Column(JSON)  # Verschlüsselte App-Liste

# 3. Key-Management
class Family(Base):
    encrypted_key = Column(String)  # Mit Nutzerpasswort verschlüsselt
    key_salt = Column(String)
    recovery_code_hash = Column(String)  # 12-Wort-Recovery-Phrase
```

**Risiken**:
- Datenverlust bei Key-Vergessen (Lösung: Recovery-Codes)
- Minimaler Performance-Overhead

### Phase 2: Erweitert (Aufwand: 1-2 Wochen, Performance: ±15%)

```typescript
// Client-seitige Nutzungsdaten-Verarbeitung
function processUsageData(usage: UsageEvent) {
  // 1. Aggregation
  const dailyHash = sha256(`${usage.childId}:${usage.date}:${usage.totalMinutes}`);

  // 2. Selective Encryption
  const encrypted = {
    ...usage,
    appPackage: encrypt(usage.appPackage, familyKey),
    duration: encrypt(usage.duration.toString(), familyKey)
  };

  return { dailyHash, encrypted };
}
```

**Risiken**:
- Komplexere Fehlerbehandlung
- Synchronisationsprobleme möglich

### Phase 3: Zero-Knowledge (Aufwand: 3-4 Wochen, Performance: ±25%)

```typescript
// Quest-Verifikation mit ZKP
async function verifyQuest(photo: File, requirements: QuestRequirements) {
  // 1. Client generiert Proof
  const { proof, publicSignals } = await generateZKProof(
    photo,
    requirements,
    zkey
  );

  // 2. Nur Proof wird gesendet (kein Foto!)
  const response = await api.post('/verify-quest', { proof, publicSignals });

  return response.valid;
}
```

**Risiken**:
- Hohe Komplexität
- Falsch-positive/negative möglich
- Browser-Kompatibilität

## 4. Kosten-Nutzen-Analyse

| Schutzmaßnahme | Sicherheitsgewinn | Aufwand | Performance | Datenverlust-Risiko | Empfehlung |
|----------------|-------------------|---------|-------------|---------------------|------------|
| **TAN-Verschlüsselung** | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | **HOCH** |
| **App-Gruppen-Verschlüsselung** | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | **HOCH** |
| **Nutzungsdaten-Hashing** | ⭐⭐⭐ | ⭐ | ⭐⭐⭐⭐⭐ | ⭐ | **MITTEL** |
| **ZKP für Quests** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐ | **NIEDRIG** (zu komplex) |
| **Client-seitige Regeln** | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | **MITTEL** |

## 5. Praktische Empfehlung

**Implementieren Sie Phase 1 + ausgewählte Teile von Phase 2**:

```python
# 1. Familien-Key-Management (Phase 1)
def create_family_with_secure_key(name: str, password: str):
    # Generiere 256-bit Key
    family_key = os.urandom(32)

    # Verschlüssele mit Nutzerpasswort
    salt = os.urandom(16)
    encrypted_key = encrypt_with_password(family_key, password, salt)

    # Generiere Recovery-Code
    recovery_phrase = generate_recovery_phrase(12)
    recovery_hash = hash_recovery_phrase(recovery_phrase)

    # Speichere in DB
    family = Family(
        name=name,
        encrypted_key=encrypted_key,
        key_salt=salt,
        recovery_code_hash=recovery_hash
    )
    db.add(family)

    return {
        'family_id': family.id,
        'recovery_phrase': recovery_phrase  # Nur einmal anzeigen!
    }
```

**Mit diesen Maßnahmen erreichen Sie:**
- ✅ 80% des Sicherheitsgewinns
- ⚠️ Nur 20% des Implementierungsaufwands
- ⚠️ Minimale Performance-Einbußen (±5%)
- ✅ Geringes Datenverlust-Risiko (mit Recovery-Codes)

**Nicht empfehlenswert**:
- ❌ Volle Zero-Knowledge-Architektur (zu komplex)
- ❌ Client-seitige Regelauswertung (Synchronisationsprobleme)
- ❌ Homomorphe Verschlüsselung (nicht praxistauglich)

## 6. Implementierungs-Roadmap

### Woche 1: Key-Management
- [ ] Familien-Key-Generierung
- [ ] Passwort-basierte Verschlüsselung
- [ ] Recovery-Phrase-System
- [ ] Key-Rotation-Mechanismus

### Woche 2: Selektive Verschlüsselung
- [ ] TAN-Codes verschlüsseln
- [ ] App-Gruppen verschlüsseln
- [ ] Geräte-IDs hashen
- [ ] Nutzungsdaten aggregieren

### Woche 3: Testing & Sicherheit
- [ ] Penetrationstests
- [ ] Key-Recovery-Prozess testen
- [ ] Performance-Messungen
- [ ] Dokumentation

## 7. Monitoring & Wartung

### Wichtige Metriken:
- Key-Recovery-Anfragen pro Woche
- Verschlüsselungs/Entschlüsselungsfehler
- Performance-Impact auf API-Endpunkte
- Nutzerfeedback zu Usability

### Regelmäßige Aufgaben:
- Key-Rotation alle 6 Monate
- Security-Audit alle 12 Monate
- Backup-Recovery-Tests quartalsweise

## Fazit

Die empfohlene Strategie bietet eine ausgezeichnete Balance zwischen Sicherheit und Praktikabilität. Durch die Kombination aus selektiver Verschlüsselung kritischer Daten mit einem robusten Key-Management und Recovery-System können Sie die Datensicherheit deutlich erhöhen, ohne die Nutzererfahrung zu beeinträchtigen oder unnötige Komplexität einzuführen.