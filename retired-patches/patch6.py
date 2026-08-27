#!/usr/bin/env python3
"""Patch 6 (bulkwart-default-de): iOS-Auto-Zoom bei Eingabefeldern abstellen.

iOS Safari zoomt beim Fokussieren jedes Feldes mit Schriftgroesse < 16px heran.
Bulwark nutzt text-sm (0.875rem) und setzt die rem-Basis per Einstellung auf
14/16/18px -> 12.25 / 14 / 15.75px. Keine Stufe erreicht 16px, der Zoom kommt
also immer. Der Viewport traegt kein maximum-scale (bewusst - manuelles Zoomen
soll moeglich bleiben), deshalb Fix ueber die Schriftgroesse.

!important ist noetig: .text-sm ist ein Klassen-Selektor (0,1,0) und schlaegt
input/textarea (0,0,1).
"""

p = 'app/globals.css'
s = open(p).read()

MARKER = 'bulkwart-default-de: iOS-Auto-Zoom'
assert 'lucide-panel-right' in s, 'globals.css sieht unerwartet aus - Upstream geaendert, Patch pruefen'
assert MARKER not in s, 'Patch 6 bereits angewandt?'

s += """

/* Patched (%s):
   iOS Safari zoomt beim Fokus auf Felder unter 16px heran. Nur Touch-Geraete,
   damit die Desktop-Typografie unveraendert bleibt. max() statt fixer 16px,
   damit die Einstellung "Schriftgroesse: Gross" (18px Basis) weiter greift. */
@media (pointer: coarse) {
  input,
  textarea,
  select,
  [contenteditable="true"] {
    font-size: max(16px, 1rem) !important;
  }
}
""" % MARKER

open(p, 'w').write(s)
print('6: globals.css gepatcht')
