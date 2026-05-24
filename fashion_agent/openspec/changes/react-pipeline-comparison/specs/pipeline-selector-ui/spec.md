# Spec: pipeline-selector-ui

## Overview

Adds a two-button pipeline selector to the Register screen in `clothie_web`. Uses the existing `_SelectButton` widget. The selected value is persisted on `user_sessions.orchestration_mode` at session creation.

## UI Layout (within `_buildCard()`)

```
[  Boy 👦  ]  [  Girl 👧  ]        ← existing gender row (unchanged)

── Agent Mode ────────────────────   ← new section label
[  ⚡ Direct  ]  [  🔄 ReAct  ]    ← new pipeline row

Model: Gemini 2.5 Flash              ← existing model display (unchanged)
```

## State Changes in `_RegisterScreenState`

```dart
String? _selectedMode;  // 'direct' | 'react'  — new
```

## Validation

```dart
if (_selectedMode == null) {
  setState(() => _error = 'Please select your preferred agent mode.');
  return;
}
```

Validation is added in `_startChat()` after the existing gender check and before the API call.

## `createSession()` Signature Change

```dart
// api_service.dart — updated signature
Future<String> createSession(
  String userName,
  int yearOfBirth,
  String gender,
  String preferredModel,
  String orchestrationMode,   // NEW — 'direct' | 'react'
) async {
  body: jsonEncode({
    'user_name': userName,
    'year_of_birth': yearOfBirth,
    'gender': gender,
    'preferred_model': preferredModel,
    'orchestration_mode': orchestrationMode,   // NEW
  }),
```

## Call Site in `register_screen.dart`

```dart
final sessionId = await _api.createSession(
  name,
  yearInt,
  _selectedGender!,
  'gemini-2.5-flash',
  _selectedMode!,    // NEW
);
```

## Section Label Widget

```dart
// Insert between gender row and model display:
const SizedBox(height: 16),
Align(
  alignment: Alignment.centerLeft,
  child: Text(
    'Agent Mode',
    style: GoogleFonts.outfit(
      fontSize: 12,
      fontWeight: FontWeight.w600,
      color: Theme.of(context).colorScheme.onSurface.withOpacity(0.5),
      letterSpacing: 0.8,
    ),
  ),
),
const SizedBox(height: 8),
Row(
  children: [
    Expanded(
      child: _SelectButton(
        label: '⚡  Direct',
        value: 'direct',
        selected: _selectedMode == 'direct',
        onTap: () => setState(() => _selectedMode = 'direct'),
      ),
    ),
    const SizedBox(width: 12),
    Expanded(
      child: _SelectButton(
        label: '🔄  ReAct',
        value: 'react',
        selected: _selectedMode == 'react',
        onTap: () => setState(() => _selectedMode = 'react'),
      ),
    ),
  ],
),
```

## No Changes to Chat Screen

The pipeline mode is selected once at registration and never shown or changeable in the chat screen. The `ChatRouteArgs` struct does not need to carry `orchestrationMode` because the backend reads it from the session.

## Backend Validation

`CreateSessionRequest` in `api/main.py` validates:
```python
if self.orchestration_mode not in ("direct", "react"):
    raise ValueError('orchestration_mode must be "direct" or "react"')
```
